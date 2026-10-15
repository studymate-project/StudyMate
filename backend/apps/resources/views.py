import math
from datetime import timedelta

from django.conf import settings
from django.db.models import (
    Avg,
    Case,
    Count,
    Exists,
    ExpressionWrapper,
    F,
    FloatField,
    IntegerField,
    Min,
    OuterRef,
    Q,
    Subquery,
    Value,
    When,
)
from django.db import transaction
from django.db.models.functions import Cast, Coalesce, Lower, Ln, Trim
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.text import slugify
from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiTypes,
    extend_schema,
    extend_schema_view,
    inline_serializer,
)
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_201_CREATED
from rest_framework.generics import ListAPIView
from rest_framework.mixins import CreateModelMixin, ListModelMixin, RetrieveModelMixin
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet, ModelViewSet
from rest_framework.decorators import action

from apps.core.permissions import IsResourceOwnerOrReadOnly, IsVideoOwnerOrReadOnly
from apps.core.schema import BAD_REQUEST, FORBIDDEN, NOT_FOUND, UNAUTHENTICATED
from apps.education.models import Interest
from apps.interactions.models import ResourceRating, ResourceUpvote, SavedResource
from apps.interactions.serializers import ResourceRatingSerializer, SavedResourceSerializer

from .models import PublicationStatus, Resource, ResourceDownload, ResourceView, Video
from .serializers import ResourceSerializer, VideoSerializer
from .services.cloudinary import discard_cloudinary_reference, is_cloudinary_reference


POPULARITY_VIEW_WEIGHT = 0.4
POPULARITY_SAVE_WEIGHT = 0.3
POPULARITY_UPVOTE_WEIGHT = 0.3
SUBJECT_RECOMMENDATION_LIMIT = 12
SUBJECT_TRENDING_LIMIT = 3
SUBJECT_RECENT_WINDOW = timedelta(days=30)


def _rating_annotations(target_field: str) -> dict[str, object]:
    rating_queryset = ResourceRating.objects.filter(
        **{f"{target_field}_id": OuterRef("pk")}
    ).order_by().values(target_field)
    return {
        "_rating_count": Coalesce(
            Subquery(
                rating_queryset.annotate(value=Count("pk")).values("value")[:1],
                output_field=IntegerField(),
            ),
            Value(0),
        ),
        "_rating_average": Subquery(
            rating_queryset.annotate(value=Avg("rating")).values("value")[:1],
            output_field=FloatField(),
        ),
    }


def _user_rating_annotation(target_field: str, user) -> dict[str, object]:
    if not user.is_authenticated:
        return {}

    return {
        "_user_rating": Subquery(
            ResourceRating.objects.filter(
                **{f"{target_field}_id": OuterRef("pk")},
                user=user,
            ).order_by().values("rating")[:1],
            output_field=IntegerField(),
        ),
    }


def _resource_metric_annotations() -> dict[str, object]:
    return {
        "_view_count": Count("view_events", distinct=True),
        "_download_count": Count("download_events", distinct=True),
        "_save_count": Count("saved_by", distinct=True),
        "_upvote_count": Count("upvotes", distinct=True),
        **_rating_annotations("resource"),
    }


def _subject_key(value: str) -> str:
    return " ".join(value.casefold().split())


def _empty_subject_stats(name: str) -> dict[str, object]:
    return {
        "name": name,
        "content_count": 0,
        "resource_count": 0,
        "video_count": 0,
        "views": 0,
        "downloads": 0,
        "saves": 0,
        "upvotes": 0,
        "ratings": 0,
        "discussion_comments": 0,
        "discussion_likes": 0,
        "recent_content": 0,
        "recent_engagement": 0,
    }


def _merge_subject_stats(subject_stats: dict[str, dict[str, object]], rows, content_type: str) -> None:
    for row in rows:
        key = row["subject_key"]
        stats = subject_stats.setdefault(key, _empty_subject_stats(row["name"]))
        stats["name"] = min(stats["name"], row["name"])
        stats["content_count"] += int(row["content_count"] or 0)
        stats[f"{content_type}_count"] += int(row["content_count"] or 0)
        for field in ("views", "downloads", "saves", "recent_content", "recent_engagement"):
            stats[field] += int(row[field] or 0)
        stats["upvotes"] += int(row["upvote_events"] or 0)
        stats["ratings"] += int(row["rating_events"] or 0)
        stats["discussion_comments"] += int(row["discussion_comment_events"] or 0)
        stats["discussion_likes"] += int(row["discussion_like_events"] or 0)


def _resource_subject_stats(recent_cutoff):
    discussion_filter = Q(discussion_comments__status=PublicationStatus.PUBLISHED)
    return Resource.objects.filter(status=PublicationStatus.PUBLISHED).annotate(
        subject_key=Lower(Trim("subject")),
    ).values("subject_key").annotate(
        name=Min("subject"),
        content_count=Count("pk", distinct=True),
        views=Count("view_events", distinct=True),
        downloads=Count("download_events", distinct=True),
        saves=Count("saved_by", distinct=True),
        upvote_events=Count("upvotes", distinct=True),
        rating_events=Count("ratings", distinct=True),
        discussion_comment_events=Count("discussion_comments", filter=discussion_filter, distinct=True),
        discussion_like_events=Count("discussion_comments__likes", filter=discussion_filter, distinct=True),
        recent_content=Count("pk", filter=Q(created_at__gte=recent_cutoff), distinct=True),
        recent_engagement=(
            Count("view_events", filter=Q(view_events__viewed_at__gte=recent_cutoff), distinct=True)
            + Count("download_events", filter=Q(download_events__downloaded_at__gte=recent_cutoff), distinct=True)
            + Count("saved_by", filter=Q(saved_by__created_at__gte=recent_cutoff), distinct=True)
            + Count("upvotes", filter=Q(upvotes__created_at__gte=recent_cutoff), distinct=True)
            + Count("ratings", filter=Q(ratings__created_at__gte=recent_cutoff), distinct=True)
            + Count(
                "discussion_comments",
                filter=discussion_filter & Q(discussion_comments__created_at__gte=recent_cutoff),
                distinct=True,
            )
        ),
    )


def _video_subject_stats(recent_cutoff):
    discussion_filter = Q(discussion_comments__status=PublicationStatus.PUBLISHED)
    return Video.objects.filter(status=PublicationStatus.PUBLISHED).annotate(
        subject_key=Lower(Trim("subject")),
    ).values("subject_key").annotate(
        name=Min("subject"),
        content_count=Count("pk", distinct=True),
        views=Value(0, output_field=IntegerField()),
        downloads=Value(0, output_field=IntegerField()),
        saves=Value(0, output_field=IntegerField()),
        upvote_events=Value(0, output_field=IntegerField()),
        rating_events=Count("ratings", distinct=True),
        discussion_comment_events=Count("discussion_comments", filter=discussion_filter, distinct=True),
        discussion_like_events=Count("discussion_comments__likes", filter=discussion_filter, distinct=True),
        recent_content=Count("pk", filter=Q(created_at__gte=recent_cutoff), distinct=True),
        recent_engagement=(
            Count("ratings", filter=Q(ratings__created_at__gte=recent_cutoff), distinct=True)
            + Count(
                "discussion_comments",
                filter=discussion_filter & Q(discussion_comments__created_at__gte=recent_cutoff),
                distinct=True,
            )
        ),
    )


def _academic_subject_keys(profile):
    exact_level = set()
    course_level = set()
    filters = Q()
    if profile.academic_level_id:
        filters |= Q(academic_level_id=profile.academic_level_id)
    if profile.course_id:
        filters |= Q(academic_level__course_id=profile.course_id)
    if not filters:
        return exact_level, course_level

    for model in (Resource, Video):
        rows = model.objects.filter(status=PublicationStatus.PUBLISHED).filter(filters).annotate(
            subject_key=Lower(Trim("subject")),
        ).values("subject_key", "academic_level_id", "academic_level__course_id").distinct()
        for row in rows:
            if profile.academic_level_id and row["academic_level_id"] == profile.academic_level_id:
                exact_level.add(row["subject_key"])
            if profile.course_id and row["academic_level__course_id"] == profile.course_id:
                course_level.add(row["subject_key"])
    return exact_level, course_level


def _catalog_subject_keys(profile):
    interest_keys = set()
    course_interest_keys = set()
    selected_subjects = {}
    course_subjects = {}
    if profile.student_interests.exists():
        selected = profile.student_interests.select_related("interest").filter(interest__is_active=True)
        for name, slug in selected.values_list("interest__name", "interest__slug"):
            interest_keys.update({_subject_key(name), _subject_key(slug)})
            selected_subjects[_subject_key(name)] = name
    if profile.course_id:
        course_interests = Interest.objects.filter(
            is_active=True,
            courses__pk=profile.course_id,
        ).values_list("name", "slug")
        for name, slug in course_interests:
            course_interest_keys.update({_subject_key(name), _subject_key(slug)})
            course_subjects[_subject_key(name)] = name
    return interest_keys, course_interest_keys, selected_subjects, course_subjects


def _subject_recommendation_score(stats, relevance):
    popularity = (
        POPULARITY_VIEW_WEIGHT * math.log1p(stats["views"])
        + 0.15 * math.log1p(stats["downloads"])
        + POPULARITY_SAVE_WEIGHT * math.log1p(stats["saves"])
        + POPULARITY_UPVOTE_WEIGHT * math.log1p(stats["upvotes"])
        + 0.1 * math.log1p(stats["ratings"] + stats["discussion_comments"] + stats["discussion_likes"])
    )
    recent = 0.5 * math.log1p(stats["recent_engagement"]) + 0.25 * math.log1p(stats["recent_content"])
    return popularity + recent + relevance


def _subject_recommendations(user, limit):
    recent_cutoff = timezone.now() - SUBJECT_RECENT_WINDOW
    subject_stats = {}
    _merge_subject_stats(subject_stats, _resource_subject_stats(recent_cutoff), "resource")
    _merge_subject_stats(subject_stats, _video_subject_stats(recent_cutoff), "video")

    profile = getattr(user, "student_profile", None)
    profile_complete = bool(profile and profile.onboarding_completed)
    exact_level_keys = course_level_keys = interest_keys = course_interest_keys = set()
    selected_subjects = {}
    course_subjects = {}
    if profile_complete:
        exact_level_keys, course_level_keys = _academic_subject_keys(profile)
        interest_keys, course_interest_keys, selected_subjects, course_subjects = _catalog_subject_keys(profile)
        for key, name in {**course_subjects, **selected_subjects}.items():
            subject_stats.setdefault(key, _empty_subject_stats(name))

    recommendations = []
    for key, stats in subject_stats.items():
        relevance = 0
        if key in exact_level_keys:
            relevance += 2.0
        elif key in course_level_keys:
            relevance += 1.25
        if key in interest_keys:
            relevance += 1.5
        elif key in course_interest_keys:
            relevance += 0.75
        stats["engagement_count"] = sum(
            stats[field]
            for field in ("views", "downloads", "saves", "upvotes", "ratings", "discussion_comments", "discussion_likes")
        )
        stats["score"] = _subject_recommendation_score(stats, relevance)
        stats["relevance"] = relevance
        recommendations.append((key, stats))

    if profile_complete:
        relevant = [item for item in recommendations if item[1]["relevance"] > 0]
        if relevant:
            other = [item for item in recommendations if item[1]["relevance"] == 0]
            recommendations = relevant + other

    recommendations.sort(key=lambda item: (-item[1]["score"], -item[1]["recent_engagement"], -item[1]["content_count"], item[1]["name"].casefold()))
    trending_keys = {
        key
        for key, _ in sorted(
            (item for item in recommendations if item[1]["recent_engagement"] > 0),
            key=lambda item: (-item[1]["recent_engagement"], -item[1]["content_count"], item[1]["name"].casefold()),
        )[:SUBJECT_TRENDING_LIMIT]
    }

    results = []
    for key, stats in recommendations[:limit]:
        results.append(
            {
                "name": stats["name"],
                "slug": slugify(stats["name"]),
                "content_count": stats["content_count"],
                "engagement_count": stats["engagement_count"],
                "recent_engagement_count": stats["recent_engagement"],
                "is_personalized": stats["relevance"] > 0,
                "is_trending": key in trending_keys,
            }
        )
    return {
        "results": results,
        "count": len(results),
        "profile_complete": profile_complete,
        "has_interests": bool(interest_keys),
    }


RESOURCE_LIST_PARAMETERS = [
    OpenApiParameter("search", OpenApiTypes.STR, OpenApiParameter.QUERY, description="Search title, subject, topic, description, or tags."),
    OpenApiParameter("subject", OpenApiTypes.STR, OpenApiParameter.QUERY, description="Case-insensitive subject filter."),
    OpenApiParameter("topic", OpenApiTypes.STR, OpenApiParameter.QUERY, description="Case-insensitive topic filter."),
    OpenApiParameter(
        "resource_type",
        OpenApiTypes.STR,
        OpenApiParameter.QUERY,
        enum=[value for value, _ in Resource.ResourceType.choices],
        description="Resource type filter.",
    ),
    OpenApiParameter(
        "academic_level",
        OpenApiTypes.STR,
        OpenApiParameter.QUERY,
        description="Academic-level ID, slug, or name.",
    ),
    OpenApiParameter(
        "difficulty",
        OpenApiTypes.STR,
        OpenApiParameter.QUERY,
        enum=[value for value, _ in Resource.Difficulty.choices],
        description="Difficulty filter.",
    ),
    OpenApiParameter(
        "tags",
        OpenApiTypes.STR,
        OpenApiParameter.QUERY,
        many=True,
        description="One or more tag IDs/slugs/names; repeat the parameter for multiple tags.",
    ),
    OpenApiParameter(
        "ordering",
        OpenApiTypes.STR,
        OpenApiParameter.QUERY,
        enum=["latest", "popular", "top_rated", "top rated", "most_downloaded", "most downloaded"],
        description="Ordering option; omitted values use the endpoint's default ordering.",
    ),
    OpenApiParameter(
        "uploader",
        OpenApiTypes.INT,
        OpenApiParameter.QUERY,
        description="Filter resources owned by one user ID.",
    ),
]

RESOURCE_INTERACTION_RESPONSE = inline_serializer(
    "ResourceInteractionResponse",
    fields={
        "upvoted": serializers.BooleanField(read_only=True),
        "resource": serializers.IntegerField(read_only=True),
        "upvotes": serializers.IntegerField(read_only=True),
    },
)
SAVED_RESOURCE_DELETE_RESPONSE = inline_serializer(
    "SavedResourceDeleteResponse",
    fields={
        "saved": serializers.BooleanField(read_only=True),
        "resource": serializers.IntegerField(read_only=True),
    },
)
RESOURCE_VIEW_RESPONSE = inline_serializer(
    "ResourceViewResponse",
    fields={
        "viewed": serializers.BooleanField(read_only=True),
        "resource": serializers.IntegerField(read_only=True),
        "views": serializers.IntegerField(read_only=True),
    },
)
RESOURCE_DOWNLOAD_RESPONSE = inline_serializer(
    "ResourceDownloadResponse",
    fields={
        "downloaded": serializers.BooleanField(read_only=True),
        "resource": serializers.IntegerField(read_only=True),
        "downloads": serializers.IntegerField(read_only=True),
    },
)
RESOURCE_RATING_DELETE_RESPONSE = inline_serializer(
    "ResourceRatingDeleteResponse",
    fields={
        "rated": serializers.BooleanField(read_only=True),
        "resource": serializers.IntegerField(read_only=True, required=False),
        "video": serializers.IntegerField(read_only=True, required=False),
    },
)


@extend_schema_view(
    list=extend_schema(
        summary="List resources",
        description="Public resources are listed with page-number pagination. Authenticated owners also see their own non-published resources. Invalid choice or catalog filters return an empty result set.",
        tags=["resources", "search / filtering"],
        parameters=RESOURCE_LIST_PARAMETERS,
        responses=ResourceSerializer(many=True),
    ),
    retrieve=extend_schema(
        summary="Get a resource",
        responses={200: ResourceSerializer, 404: NOT_FOUND},
    ),
    create=extend_schema(
        summary="Create a resource",
        description="The server sets uploader, slug, status, and counters. Link resources require external_url.",
        request=ResourceSerializer,
        responses={201: ResourceSerializer, 400: BAD_REQUEST, 401: UNAUTHENTICATED},
    ),
    update=extend_schema(
        summary="Replace a resource",
        description="Ownership and server-controlled fields cannot be reassigned through the request.",
        request=ResourceSerializer,
        responses={200: ResourceSerializer, 400: BAD_REQUEST, 401: UNAUTHENTICATED, 403: FORBIDDEN, 404: NOT_FOUND},
    ),
    partial_update=extend_schema(
        summary="Update a resource",
        description="Ownership and server-controlled fields cannot be reassigned through the request.",
        request=ResourceSerializer,
        responses={200: ResourceSerializer, 400: BAD_REQUEST, 401: UNAUTHENTICATED, 403: FORBIDDEN, 404: NOT_FOUND},
    ),
    destroy=extend_schema(
        summary="Delete a resource",
        responses={204: None, 401: UNAUTHENTICATED, 403: FORBIDDEN, 404: NOT_FOUND},
    ),
)
class ResourceViewSet(ModelViewSet):
    serializer_class = ResourceSerializer
    permission_classes = (IsResourceOwnerOrReadOnly,)
    lookup_field = "slug"
    lookup_url_kwarg = "lookup"
    _write_throttle_scope = "resource_write"

    def get_throttles(self):
        self.throttle_scope = self._write_throttle_scope if self.action == "create" else None
        return super().get_throttles()
    http_method_names = ("get", "post", "put", "patch", "delete", "head", "options")

    def get_queryset(self):
        queryset = Resource.objects.select_related("uploader", "academic_level").prefetch_related("tags").annotate(
            **_resource_metric_annotations(),
            **_user_rating_annotation("resource", self.request.user),
        ).order_by("-created_at", "-pk")
        if self.request.user.is_authenticated:
            queryset = queryset.annotate(
                _is_saved=Exists(
                    SavedResource.objects.filter(
                        resource_id=OuterRef("pk"),
                        user=self.request.user,
                    )
                )
            )
            return queryset.filter(Q(status=PublicationStatus.PUBLISHED) | Q(uploader=self.request.user))
        return queryset.filter(status=PublicationStatus.PUBLISHED)

    def _requested_ordering(self):
        value = self.request.query_params.get("ordering")
        if value is None:
            return None

        return {
            "latest": "latest",
            "popular": "popular",
            "top rated": "top_rated",
            "top_rated": "top_rated",
            "most downloaded": "most_downloaded",
            "most_downloaded": "most_downloaded",
        }.get(value.strip().casefold())

    def _rating_prior(self) -> float:
        if self.request.user.is_authenticated:
            visible_resources = Resource.objects.filter(
                Q(status=PublicationStatus.PUBLISHED) | Q(uploader=self.request.user)
            )
        else:
            visible_resources = Resource.objects.filter(status=PublicationStatus.PUBLISHED)
        prior = ResourceRating.objects.filter(
            resource_id__in=visible_resources.values("pk")
        ).aggregate(value=Avg("rating"))["value"]
        return float(prior) if prior is not None else 0.0

    @staticmethod
    def _log_count(annotation_name: str):
        return Ln(Cast(F(annotation_name), FloatField()) + Value(1.0))

    def _apply_ordering(self, queryset, ordering):
        if ordering is None:
            return queryset.order_by("-created_at", "-pk")
        if ordering == "latest":
            return queryset.order_by("-created_at", "-pk")
        if ordering == "popular":
            # Log-scaled counts prevent high-volume views from overwhelming saves
            # and upvotes. The weights sum to one and are intentionally stable.
            popularity_score = ExpressionWrapper(
                Value(POPULARITY_VIEW_WEIGHT, output_field=FloatField()) * self._log_count("_view_count")
                + Value(POPULARITY_SAVE_WEIGHT, output_field=FloatField()) * self._log_count("_save_count")
                + Value(POPULARITY_UPVOTE_WEIGHT, output_field=FloatField()) * self._log_count("_upvote_count"),
                output_field=FloatField(),
            )
            return queryset.annotate(_popularity_score=popularity_score).order_by(
                "-_popularity_score",
                "-_view_count",
                "-_save_count",
                "-_upvote_count",
                "-created_at",
                "-pk",
            )
        if ordering == "top_rated":
            prior = Value(self._rating_prior(), output_field=FloatField())
            minimum_count = Value(float(settings.RESOURCE_RATING_MIN_COUNT), output_field=FloatField())
            rating_count = Cast(F("_rating_count"), FloatField())
            average_rating = Coalesce(F("_rating_average"), prior)
            bayesian_score = Case(
                When(
                    _rating_count__gt=0,
                    then=ExpressionWrapper(
                        (rating_count / (rating_count + minimum_count)) * average_rating
                        + (minimum_count / (rating_count + minimum_count)) * prior,
                        output_field=FloatField(),
                    ),
                ),
                default=prior,
                output_field=FloatField(),
            )
            return queryset.annotate(_bayesian_rating_score=bayesian_score).order_by(
                "-_bayesian_rating_score",
                "-_rating_count",
                "-_rating_average",
                "-created_at",
                "-pk",
            )
        if ordering == "most_downloaded":
            return queryset.order_by("-_download_count", "-created_at", "-pk")
        return queryset

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        if self.action != "list":
            return queryset

        tag_filter_applied = False

        for field in ("subject", "topic"):
            value = self.request.query_params.get(field)
            if value is not None:
                queryset = queryset.filter(**{f"{field}__iexact": value.strip()})

        uploader = self.request.query_params.get("uploader")
        if uploader is not None:
            try:
                uploader_id = int(uploader)
            except (TypeError, ValueError):
                return queryset.none()
            if uploader_id < 1:
                return queryset.none()
            queryset = queryset.filter(uploader_id=uploader_id)

        for field, choices in (
            ("resource_type", Resource.ResourceType.choices),
            ("difficulty", Resource.Difficulty.choices),
        ):
            value = self.request.query_params.get(field)
            if value is None:
                continue

            normalized_value = value.strip().casefold()
            matching_value = next(
                (
                    choice_value
                    for choice_value, label in choices
                    if normalized_value in {choice_value.casefold(), label.casefold()}
                ),
                None,
            )
            if matching_value is None:
                return queryset.none()
            queryset = queryset.filter(**{field: matching_value})

        academic_level = self.request.query_params.get("academic_level")
        if academic_level is not None:
            academic_level = academic_level.strip()
            if academic_level.isdigit():
                academic_level_id = int(academic_level)
                if academic_level_id > 2**63 - 1:
                    return queryset.none()
                queryset = queryset.filter(academic_level_id=academic_level_id)
            else:
                queryset = queryset.filter(
                    Q(academic_level__slug__iexact=academic_level)
                    | Q(academic_level__name__iexact=academic_level)
                )

        tag_values = [value.strip() for value in self.request.query_params.getlist("tags") if value.strip()]
        if tag_values:
            tag_filter_applied = True
            tag_query = Q()
            for tag_value in tag_values:
                tag_query |= Q(tags__slug__iexact=tag_value) | Q(tags__name__iexact=tag_value)
            queryset = queryset.filter(tag_query)
        elif "tags" in self.request.query_params:
            return queryset.none()

        ordering = self._requested_ordering()
        search_term = self.request.query_params.get("search", "").strip()
        if not search_term:
            queryset = queryset.distinct() if tag_filter_applied else queryset
            return self._apply_ordering(queryset, ordering)

        title_match = Q(title__icontains=search_term)
        subject_or_topic_match = (
            Q(subject__icontains=search_term)
            | Q(topic__icontains=search_term)
            | Q(course__icontains=search_term)
            | Q(semester__icontains=search_term)
        )
        description_match = Q(description__icontains=search_term)
        tag_match = Q(tags__name__icontains=search_term) | Q(tags__slug__icontains=search_term)

        queryset = (
            queryset.filter(title_match | subject_or_topic_match | description_match | tag_match)
            .annotate(
                search_rank=Case(
                    When(title_match, then=Value(4)),
                    When(subject_or_topic_match, then=Value(3)),
                    When(description_match, then=Value(2)),
                    When(tag_match, then=Value(1)),
                    default=Value(0),
                    output_field=IntegerField(),
                )
            )
            .distinct()
        )
        return self._apply_ordering(queryset, ordering) if ordering else queryset.order_by(
            "-search_rank", "-created_at", "-pk"
        )

    def get_permissions(self):
        if self.action == "subject_recommendations":
            return [IsAuthenticated()]
        if self.action in {"list", "retrieve"}:
            return [AllowAny()]
        return [IsAuthenticated(), IsResourceOwnerOrReadOnly()]

    @extend_schema(
        summary="Recommend subjects for the authenticated student",
        description="Rank published subjects using academic-level relevance, selected/course interests, engagement, and recent activity.",
        parameters=[
            OpenApiParameter(
                "limit",
                OpenApiTypes.INT,
                OpenApiParameter.QUERY,
                description="Maximum number of subjects to return.",
            ),
        ],
        responses=inline_serializer(
            "SubjectRecommendationResponse",
            fields={
                "results": serializers.ListField(child=serializers.DictField()),
                "count": serializers.IntegerField(),
                "profile_complete": serializers.BooleanField(),
                "has_interests": serializers.BooleanField(),
            },
        ),
    )
    @action(detail=False, methods=("get",), url_path="subjects")
    def subject_recommendations(self, request):
        raw_limit = request.query_params.get("limit", SUBJECT_RECOMMENDATION_LIMIT)
        try:
            limit = max(1, min(int(raw_limit), 24))
        except (TypeError, ValueError):
            limit = SUBJECT_RECOMMENDATION_LIMIT
        return Response(_subject_recommendations(request.user, limit))

    def get_object(self):
        lookup = self.kwargs[self.lookup_url_kwarg]
        queryset = self.filter_queryset(self.get_queryset())
        if self.action in {"update", "partial_update", "destroy"} and lookup.isdigit():
            obj = get_object_or_404(queryset, pk=int(lookup))
        else:
            obj = get_object_or_404(queryset, slug=lookup)
        self.check_object_permissions(self.request, obj)
        return obj

    def perform_create(self, serializer):
        serializer.save(uploader=self.request.user, status=PublicationStatus.PUBLISHED)

    def perform_destroy(self, instance):
        old_reference = instance.file.name if instance.file and is_cloudinary_reference(instance.file.name) else None
        with transaction.atomic():
            instance.delete()
            if old_reference:
                transaction.on_commit(lambda: discard_cloudinary_reference(old_reference))


@extend_schema_view(
    get=extend_schema(
        summary="List saved resources",
        description="Return only resources saved by the authenticated user.",
        responses={200: ResourceSerializer(many=True), 401: UNAUTHENTICATED},
    ),
)
class SavedResourceListView(ListAPIView):
    """List resources saved by the authenticated user."""

    serializer_class = ResourceSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        queryset = Resource.objects.select_related("uploader", "academic_level").prefetch_related("tags").annotate(
            **_resource_metric_annotations(),
            **_user_rating_annotation("resource", self.request.user),
            _is_saved=Value(True),
        ).order_by("-created_at", "-pk")
        return queryset.filter(
            Q(saved_by__user=self.request.user)
            & (Q(status=PublicationStatus.PUBLISHED) | Q(uploader=self.request.user))
        ).distinct()


@extend_schema_view(
    list=extend_schema(
        summary="List videos",
        responses=VideoSerializer(many=True),
    ),
    retrieve=extend_schema(
        summary="Get a video",
        responses={200: VideoSerializer, 404: NOT_FOUND},
    ),
    create=extend_schema(
        summary="Create a YouTube video resource",
        description="youtube_url accepts supported YouTube watch, youtu.be, and embed URLs; it is normalized to youtube_video_id.",
        request=VideoSerializer,
        responses={201: VideoSerializer, 400: BAD_REQUEST, 401: UNAUTHENTICATED},
    ),
)
class VideoViewSet(ListModelMixin, RetrieveModelMixin, CreateModelMixin, GenericViewSet):
    serializer_class = VideoSerializer
    permission_classes = (IsVideoOwnerOrReadOnly,)
    lookup_field = "slug"

    def get_throttles(self):
        self.throttle_scope = "resource_write" if self.action == "create" else None
        return super().get_throttles()

    def get_queryset(self):
        queryset = Video.objects.select_related("uploader", "academic_level").prefetch_related("tags").annotate(
            **_rating_annotations("video"),
            **_user_rating_annotation("video", self.request.user),
        )
        if self.request.user.is_authenticated:
            return queryset.filter(Q(status=PublicationStatus.PUBLISHED) | Q(uploader=self.request.user))
        return queryset.filter(status=PublicationStatus.PUBLISHED)

    def get_permissions(self):
        if self.action in {"list", "retrieve"}:
            return [AllowAny()]
        if self.action not in {"create"}:
            return [AllowAny()]
        return [IsAuthenticated(), IsVideoOwnerOrReadOnly()]

    def perform_create(self, serializer):
        serializer.save(uploader=self.request.user, status=PublicationStatus.PUBLISHED)


class ResourceInteractionView(APIView):
    """Base view for authenticated resource interactions."""

    permission_classes = (IsAuthenticated,)

    def get_resource(self, request, resource_id):
        queryset = Resource.objects.filter(status=PublicationStatus.PUBLISHED)
        if request.user.is_authenticated:
            queryset = Resource.objects.filter(
                Q(status=PublicationStatus.PUBLISHED) | Q(uploader=request.user)
            )
        return get_object_or_404(queryset, pk=resource_id)


class ResourceRatingView(ResourceInteractionView):
    """Create, update, or remove the authenticated user's resource rating."""

    throttle_scope = "interaction_write"

    def _save_rating(self, request, resource_id, *, partial=False):
        resource = self.get_resource(request, resource_id)
        existing = ResourceRating.objects.filter(user=request.user, resource=resource).first()
        serializer = ResourceRatingSerializer(
            instance=existing,
            data=request.data,
            partial=partial and existing is not None,
        )
        serializer.is_valid(raise_exception=True)
        rating = serializer.save(user=request.user, resource=resource)
        return Response(
            ResourceRatingSerializer(rating).data,
            status=HTTP_200_OK if existing else HTTP_201_CREATED,
        )

    @extend_schema(
        request=ResourceRatingSerializer,
        responses={201: ResourceRatingSerializer, 200: ResourceRatingSerializer, 400: BAD_REQUEST, 401: UNAUTHENTICATED, 404: NOT_FOUND},
    )
    def post(self, request, resource_id):
        return self._save_rating(request, resource_id)

    @extend_schema(
        request=ResourceRatingSerializer,
        responses={200: ResourceRatingSerializer, 400: BAD_REQUEST, 401: UNAUTHENTICATED, 404: NOT_FOUND},
    )
    def put(self, request, resource_id):
        return self._save_rating(request, resource_id)

    @extend_schema(
        request=ResourceRatingSerializer,
        responses={200: ResourceRatingSerializer, 400: BAD_REQUEST, 401: UNAUTHENTICATED, 404: NOT_FOUND},
    )
    def patch(self, request, resource_id):
        return self._save_rating(request, resource_id, partial=True)

    @extend_schema(
        request=None,
        responses={200: RESOURCE_RATING_DELETE_RESPONSE, 401: UNAUTHENTICATED, 404: NOT_FOUND},
    )
    def delete(self, request, resource_id):
        resource = self.get_resource(request, resource_id)
        ResourceRating.objects.filter(user=request.user, resource=resource).delete()
        return Response({"rated": False, "resource": resource.pk}, status=HTTP_200_OK)


class ResourceSaveView(ResourceInteractionView):
    """Create or remove the authenticated user's saved-resource relationship."""

    throttle_scope = "interaction_write"

    @extend_schema(
        summary="Save a resource",
        request=None,
        responses={201: SavedResourceSerializer, 200: SavedResourceSerializer, 401: UNAUTHENTICATED, 404: NOT_FOUND},
    )
    def post(self, request, resource_id):
        resource = self.get_resource(request, resource_id)
        saved, created = SavedResource.objects.get_or_create(
            user=request.user,
            resource=resource,
        )
        return Response(
            SavedResourceSerializer(saved).data,
            status=HTTP_201_CREATED if created else HTTP_200_OK,
        )

    @extend_schema(
        summary="Unsave a resource",
        request=None,
        responses={200: SAVED_RESOURCE_DELETE_RESPONSE, 401: UNAUTHENTICATED, 404: NOT_FOUND},
    )
    def delete(self, request, resource_id):
        resource = self.get_resource(request, resource_id)
        SavedResource.objects.filter(user=request.user, resource=resource).delete()
        return Response(
            {"saved": False, "resource": resource.pk},
            status=HTTP_200_OK,
        )


class ResourceUpvoteView(ResourceInteractionView):
    """Create or remove the authenticated user's resource upvote."""

    throttle_scope = "interaction_write"

    @extend_schema(
        summary="Upvote a resource",
        request=None,
        responses={201: RESOURCE_INTERACTION_RESPONSE, 200: RESOURCE_INTERACTION_RESPONSE, 401: UNAUTHENTICATED, 404: NOT_FOUND},
    )
    def post(self, request, resource_id):
        resource = self.get_resource(request, resource_id)
        _, created = ResourceUpvote.objects.get_or_create(
            user=request.user,
            resource=resource,
        )
        return Response(
            {
                "upvoted": True,
                "resource": resource.pk,
                "upvotes": ResourceUpvote.objects.filter(resource=resource).count(),
            },
            status=HTTP_201_CREATED if created else HTTP_200_OK,
        )

    @extend_schema(
        summary="Remove a resource upvote",
        request=None,
        responses={200: RESOURCE_INTERACTION_RESPONSE, 401: UNAUTHENTICATED, 404: NOT_FOUND},
    )
    def delete(self, request, resource_id):
        resource = self.get_resource(request, resource_id)
        ResourceUpvote.objects.filter(user=request.user, resource=resource).delete()
        return Response(
            {
                "upvoted": False,
                "resource": resource.pk,
                "upvotes": ResourceUpvote.objects.filter(resource=resource).count(),
            },
            status=HTTP_200_OK,
        )


class VideoRatingView(APIView):
    """Create, update, or remove the authenticated user's video rating."""

    permission_classes = (IsAuthenticated,)
    throttle_scope = "interaction_write"

    def get_video(self, request, video_slug):
        queryset = Video.objects.filter(status=PublicationStatus.PUBLISHED)
        if request.user.is_authenticated:
            queryset = Video.objects.filter(
                Q(status=PublicationStatus.PUBLISHED) | Q(uploader=request.user)
            )
        return get_object_or_404(queryset, slug=video_slug)

    def _save_rating(self, request, video_slug, *, partial=False):
        video = self.get_video(request, video_slug)
        existing = ResourceRating.objects.filter(user=request.user, video=video).first()
        serializer = ResourceRatingSerializer(
            instance=existing,
            data=request.data,
            partial=partial and existing is not None,
        )
        serializer.is_valid(raise_exception=True)
        rating = serializer.save(user=request.user, video=video)
        return Response(
            ResourceRatingSerializer(rating).data,
            status=HTTP_200_OK if existing else HTTP_201_CREATED,
        )

    @extend_schema(
        request=ResourceRatingSerializer,
        responses={201: ResourceRatingSerializer, 200: ResourceRatingSerializer, 400: BAD_REQUEST, 401: UNAUTHENTICATED, 404: NOT_FOUND},
    )
    def post(self, request, video_slug):
        return self._save_rating(request, video_slug)

    @extend_schema(
        request=ResourceRatingSerializer,
        responses={200: ResourceRatingSerializer, 400: BAD_REQUEST, 401: UNAUTHENTICATED, 404: NOT_FOUND},
    )
    def put(self, request, video_slug):
        return self._save_rating(request, video_slug)

    @extend_schema(
        request=ResourceRatingSerializer,
        responses={200: ResourceRatingSerializer, 400: BAD_REQUEST, 401: UNAUTHENTICATED, 404: NOT_FOUND},
    )
    def patch(self, request, video_slug):
        return self._save_rating(request, video_slug, partial=True)

    @extend_schema(
        request=None,
        responses={200: RESOURCE_RATING_DELETE_RESPONSE, 401: UNAUTHENTICATED, 404: NOT_FOUND},
    )
    def delete(self, request, video_slug):
        video = self.get_video(request, video_slug)
        ResourceRating.objects.filter(user=request.user, video=video).delete()
        return Response({"rated": False, "video": video.pk}, status=HTTP_200_OK)


class ResourceEventView(ResourceInteractionView):
    """Base view for explicit, backend-recorded resource events."""

    permission_classes = (AllowAny,)
    throttle_scope = "event_write"

    @staticmethod
    def request_user_or_none(request):
        return request.user if request.user.is_authenticated else None


class ResourceViewTrackView(ResourceEventView):
    """Record one explicit resource-view event without accepting counters."""

    @extend_schema(
        summary="Record a resource view",
        request=None,
        responses={201: RESOURCE_VIEW_RESPONSE, 404: NOT_FOUND},
    )
    def post(self, request, resource_id):
        resource = self.get_resource(request, resource_id)
        ResourceView.objects.create(
            resource=resource,
            user=self.request_user_or_none(request),
        )
        return Response(
            {
                "viewed": True,
                "resource": resource.pk,
                "views": ResourceView.objects.filter(resource=resource).count(),
            },
            status=HTTP_201_CREATED,
        )


class ResourceDownloadTrackView(ResourceEventView):
    """Record one explicit resource-download event without accepting counters."""

    @extend_schema(
        summary="Record a resource download",
        request=None,
        responses={201: RESOURCE_DOWNLOAD_RESPONSE, 404: NOT_FOUND},
    )
    def post(self, request, resource_id):
        resource = self.get_resource(request, resource_id)
        ResourceDownload.objects.create(
            resource=resource,
            user=self.request_user_or_none(request),
        )
        return Response(
            {
                "downloaded": True,
                "resource": resource.pk,
                "downloads": ResourceDownload.objects.filter(resource=resource).count(),
            },
            status=HTTP_201_CREATED,
        )
