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
    OuterRef,
    Q,
    Subquery,
    Value,
    When,
)
from django.db import transaction
from django.db.models.functions import Cast, Coalesce, Ln
from django.shortcuts import get_object_or_404
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

from apps.core.permissions import IsResourceOwnerOrReadOnly, IsVideoOwnerOrReadOnly
from apps.core.schema import BAD_REQUEST, FORBIDDEN, NOT_FOUND, UNAUTHENTICATED
from apps.interactions.models import ResourceRating, ResourceUpvote, SavedResource
from apps.interactions.serializers import ResourceRatingSerializer, SavedResourceSerializer

from .models import PublicationStatus, Resource, ResourceDownload, ResourceView, Video
from .serializers import ResourceSerializer, VideoSerializer
from .services.cloudinary import discard_cloudinary_reference, is_cloudinary_reference


POPULARITY_VIEW_WEIGHT = 0.4
POPULARITY_SAVE_WEIGHT = 0.3
POPULARITY_UPVOTE_WEIGHT = 0.3


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
        if self.action in {"list", "retrieve"}:
            return [AllowAny()]
        return [IsAuthenticated(), IsResourceOwnerOrReadOnly()]

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
        serializer.save(uploader=self.request.user)


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
