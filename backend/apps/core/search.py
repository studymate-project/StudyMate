from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from django.contrib.postgres.search import SearchQuery, SearchRank, TrigramSimilarity
from django.db import connection, transaction
from django.db.models import ExpressionWrapper, F, FloatField, Q, Value
from django.db.models.functions import Greatest
from django.urls import reverse
from rest_framework import serializers
from rest_framework.request import Request

from apps.community.models import Question
from apps.resources.models import PublicationStatus, Resource, Video


MAX_QUERY_LENGTH = 200
DEFAULT_SEARCH_LIMIT = 20
MAX_SEARCH_LIMIT = 50
MAX_SEARCH_OFFSET = 1000
TRIGRAM_SIMILARITY_THRESHOLD = 0.15
SNIPPET_LENGTH = 240


class SearchRequestSerializer(serializers.Serializer):
    q = serializers.CharField(
        required=True,
        allow_blank=False,
        max_length=MAX_QUERY_LENGTH,
        trim_whitespace=True,
    )
    limit = serializers.IntegerField(
        required=False,
        default=DEFAULT_SEARCH_LIMIT,
        min_value=1,
        max_value=MAX_SEARCH_LIMIT,
    )
    offset = serializers.IntegerField(
        required=False,
        default=0,
        min_value=0,
        max_value=MAX_SEARCH_OFFSET,
    )


class SearchResultSerializer(serializers.Serializer):
    type = serializers.ChoiceField(choices=("resource", "video", "question"), read_only=True)
    id = serializers.IntegerField(read_only=True)
    title = serializers.CharField(read_only=True)
    snippet = serializers.CharField(read_only=True, allow_blank=True)
    metadata = serializers.DictField(read_only=True)
    detail_url = serializers.CharField(read_only=True)
    score = serializers.FloatField(read_only=True)


class SearchResponseSerializer(serializers.Serializer):
    query = serializers.CharField(read_only=True)
    results = SearchResultSerializer(many=True, read_only=True)
    limit = serializers.IntegerField(read_only=True)
    offset = serializers.IntegerField(read_only=True)
    has_more = serializers.BooleanField(read_only=True)
    next_offset = serializers.IntegerField(read_only=True, allow_null=True)


@dataclass(frozen=True)
class _SearchSpec:
    model: type[Resource] | type[Video] | type[Question]
    content_type: str
    owner_field: str
    text_fields: tuple[str, ...]
    snippet_field: str
    metadata_fields: tuple[str, ...]
    detail_route: str
    detail_kwarg: str


SEARCH_SPECS = (
    _SearchSpec(
        model=Resource,
        content_type="resource",
        owner_field="uploader",
        text_fields=("title", "description", "subject", "topic", "course", "semester"),
        snippet_field="description",
        metadata_fields=("subject", "topic", "course", "semester", "resource_type"),
        detail_route="resource-detail",
        detail_kwarg="lookup",
    ),
    _SearchSpec(
        model=Video,
        content_type="video",
        owner_field="uploader",
        text_fields=("title", "description", "subject", "topic", "course", "semester"),
        snippet_field="description",
        metadata_fields=("subject", "topic", "course", "semester", "youtube_video_id"),
        detail_route="video-detail",
        detail_kwarg="slug",
    ),
    _SearchSpec(
        model=Question,
        content_type="question",
        owner_field="author",
        text_fields=("title", "body", "subject", "topic"),
        snippet_field="body",
        metadata_fields=("subject", "topic"),
        detail_route="question-detail",
        detail_kwarg="slug",
    ),
)


def normalize_search_query(value: str) -> str:
    """Normalize whitespace while rejecting database-unsafe null characters."""

    normalized = " ".join(value.split())
    if "\x00" in normalized:
        raise serializers.ValidationError({"q": "Search query contains an invalid character."})
    return normalized


def _visible_queryset(request: Request, spec: _SearchSpec):
    queryset = spec.model.objects.all()
    visibility = Q(status=PublicationStatus.PUBLISHED)
    if request.user.is_authenticated:
        visibility |= Q(**{f"{spec.owner_field}__exact": request.user})
    return queryset.filter(visibility)


def _snippet(value: str | None) -> str:
    normalized = " ".join((value or "").split())
    if len(normalized) <= SNIPPET_LENGTH:
        return normalized
    return f"{normalized[: SNIPPET_LENGTH - 3].rstrip()}..."


def _build_similarity(spec: _SearchSpec, query: str):
    return Greatest(
        *[
            # Tag text is already represented in each model's trigger-maintained
            # FTS vector; trigram matching complements FTS for typos and partial text.
            TrigramSimilarity(field, query)
            for field in spec.text_fields
        ]
    )


def _candidate_rows(request: Request, spec: _SearchSpec, query: str, candidate_limit: int) -> list[dict[str, Any]]:
    search_query = SearchQuery(query, config="english", search_type="websearch")
    similarity = _build_similarity(spec, query)
    trigram_match = Q(**{f"{spec.text_fields[0]}__trigram_similar": query})
    for field in spec.text_fields[1:]:
        trigram_match |= Q(**{f"{field}__trigram_similar": query})
    fts_rank = SearchRank(
        F("search_vector"),
        search_query,
        # SearchRank weights are ordered D, C, B, A. The trigger assigns
        # title=A, body/description/tags=B, metadata=C.
        weights=[0.1, 0.2, 0.4, 1.0],
        cover_density=True,
    )
    score = ExpressionWrapper(
        fts_rank + similarity * Value(0.25),
        output_field=FloatField(),
    )
    fields = ["pk", "slug", "title", spec.snippet_field, "created_at", *spec.metadata_fields]
    rows = (
        _visible_queryset(request, spec)
        .annotate(_trigram_similarity=similarity)
        .annotate(_search_score=score)
        .filter(Q(search_vector=search_query) | trigram_match)
        .order_by("-_search_score", "-created_at", "-pk")
        .values(*fields, "_search_score")[:candidate_limit]
    )

    results = []
    for row in rows:
        metadata = {field: row.get(field) for field in spec.metadata_fields}
        results.append(
            {
                "type": spec.content_type,
                "id": row["pk"],
                "title": row["title"],
                "snippet": _snippet(row.get(spec.snippet_field)),
                "metadata": metadata,
                "detail_url": reverse(spec.detail_route, kwargs={spec.detail_kwarg: row["slug"]}),
                "score": float(row["_search_score"] or 0),
                "_created_at": row["created_at"],
            }
        )
    return results


def search_content(request: Request, query: str, limit: int, offset: int) -> dict[str, Any]:
    """Return a bounded, globally ranked union of visible content types."""

    candidate_limit = offset + limit + 1
    with transaction.atomic():
        # The trigram GIN operator uses PostgreSQL's similarity threshold. Keep
        # the existing fuzzy-match threshold local to this read transaction so
        # pooled connections cannot leak it into another request.
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT set_config('pg_trgm.similarity_threshold', %s, true)",
                [str(TRIGRAM_SIMILARITY_THRESHOLD)],
            )
        candidates = [
            result
            for spec in SEARCH_SPECS
            for result in _candidate_rows(request, spec, query, candidate_limit)
        ]
    candidates.sort(
        key=lambda result: (
            -result["score"],
            -result["_created_at"].timestamp(),
            result["type"],
            -result["id"],
        )
    )
    page = candidates[offset : offset + limit]
    has_more = len(candidates) > offset + limit
    for result in page:
        result["score"] = round(result["score"], 6)
        result.pop("_created_at", None)

    return {
        "query": query,
        "results": page,
        "limit": limit,
        "offset": offset,
        "has_more": has_more,
        "next_offset": offset + limit if has_more else None,
    }
