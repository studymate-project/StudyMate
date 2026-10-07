from django.db.models import Q
from drf_spectacular.utils import OpenApiParameter, OpenApiTypes, extend_schema, extend_schema_view
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.viewsets import ReadOnlyModelViewSet

from .models import AcademicLevel, Course, EducationBackground, Interest, StudentInterest
from .serializers import (
    AcademicLevelSerializer,
    CourseSerializer,
    EducationBackgroundSerializer,
    InterestSerializer,
    StudentInterestSerializer,
)
from apps.core.schema import NOT_FOUND


MAX_CATALOG_PK = 2**63 - 1


def _resolve_catalog_id(model, value: str, *, active_filters: dict[str, object]) -> int | None:
    """Resolve one catalog identifier without allowing ambiguous matches."""

    value = value.strip()
    if not value:
        return None

    identifier_filter = Q(slug__iexact=value) | Q(name__iexact=value)
    if value.isdecimal() and len(value) <= 19:
        numeric_value = int(value)
        if numeric_value <= MAX_CATALOG_PK:
            identifier_filter |= Q(pk=numeric_value)

    matches = list(
        model.objects.filter(identifier_filter, **active_filters).values_list("pk", flat=True)[:2]
    )
    return matches[0] if len(matches) == 1 else None


@extend_schema_view(
    list=extend_schema(
        summary="List education backgrounds",
        responses=EducationBackgroundSerializer(many=True),
    ),
    retrieve=extend_schema(
        summary="Get an education background",
        responses={200: EducationBackgroundSerializer, 404: NOT_FOUND},
    ),
)
class EducationBackgroundViewSet(ReadOnlyModelViewSet):
    queryset = EducationBackground.objects.filter(is_active=True)
    serializer_class = EducationBackgroundSerializer
    permission_classes = (AllowAny,)


@extend_schema_view(
    list=extend_schema(
        summary="List courses",
        description="Optionally filter courses by background ID, slug, or name. An invalid relationship filter returns an empty result set.",
        parameters=[
            OpenApiParameter(
                "background",
                OpenApiTypes.STR,
                OpenApiParameter.QUERY,
                description="Education background ID, slug, or name.",
            ),
        ],
        responses=CourseSerializer(many=True),
    ),
    retrieve=extend_schema(
        summary="Get a course",
        responses={200: CourseSerializer, 404: NOT_FOUND},
    ),
)
class CourseViewSet(ReadOnlyModelViewSet):
    serializer_class = CourseSerializer
    permission_classes = (AllowAny,)

    def get_queryset(self):
        queryset = Course.objects.select_related("education_background").filter(
            is_active=True,
            education_background__is_active=True,
        )
        background = self.request.query_params.get("background")
        if background is not None:
            background_id = _resolve_catalog_id(
                EducationBackground,
                background,
                active_filters={"is_active": True},
            )
            if background_id is None:
                return queryset.none()
            queryset = queryset.filter(education_background_id=background_id)
        return queryset


@extend_schema_view(
    list=extend_schema(
        summary="List academic levels",
        description="Optionally filter levels by course ID, slug, or name. An invalid relationship filter returns an empty result set.",
        parameters=[
            OpenApiParameter(
                "course",
                OpenApiTypes.STR,
                OpenApiParameter.QUERY,
                description="Course ID, slug, or name.",
            ),
            OpenApiParameter(
                "background",
                OpenApiTypes.STR,
                OpenApiParameter.QUERY,
                description="Optional education background ID, slug, or name.",
            ),
        ],
        responses=AcademicLevelSerializer(many=True),
    ),
    retrieve=extend_schema(
        summary="Get an academic level",
        responses={200: AcademicLevelSerializer, 404: NOT_FOUND},
    ),
)
class AcademicLevelViewSet(ReadOnlyModelViewSet):
    serializer_class = AcademicLevelSerializer
    permission_classes = (AllowAny,)

    def get_queryset(self):
        queryset = AcademicLevel.objects.select_related(
            "course", "course__education_background"
        ).filter(
            is_active=True,
            course__is_active=True,
            course__education_background__is_active=True,
        )
        course = self.request.query_params.get("course")
        background = self.request.query_params.get("background")
        if course is not None:
            course_id = _resolve_catalog_id(
                Course,
                course,
                active_filters={
                    "is_active": True,
                    "education_background__is_active": True,
                },
            )
            if course_id is None:
                return queryset.none()
            queryset = queryset.filter(course_id=course_id)
        if background is not None:
            background_id = _resolve_catalog_id(
                EducationBackground,
                background,
                active_filters={"is_active": True},
            )
            if background_id is None:
                return queryset.none()
            queryset = queryset.filter(course__education_background_id=background_id)
        return queryset


@extend_schema_view(
    list=extend_schema(
        summary="List interests",
        description="Optionally filter interests to those associated with a course ID, slug, or name. An invalid relationship filter returns an empty result set.",
        parameters=[
            OpenApiParameter(
                "course",
                OpenApiTypes.STR,
                OpenApiParameter.QUERY,
                description="Course ID, slug, or name.",
            ),
        ],
        responses=InterestSerializer(many=True),
    ),
    retrieve=extend_schema(
        summary="Get an interest",
        responses={200: InterestSerializer, 404: NOT_FOUND},
    ),
)
class InterestViewSet(ReadOnlyModelViewSet):
    serializer_class = InterestSerializer
    permission_classes = (AllowAny,)

    def get_queryset(self):
        queryset = Interest.objects.filter(is_active=True)
        course = self.request.query_params.get("course")
        if course is not None:
            course_id = _resolve_catalog_id(
                Course,
                course,
                active_filters={
                    "is_active": True,
                    "education_background__is_active": True,
                },
            )
            if course_id is None:
                return queryset.none()
            queryset = queryset.filter(courses__pk=course_id).distinct()
        return queryset


@extend_schema_view(
    list=extend_schema(
        summary="List student interests",
        responses=StudentInterestSerializer(many=True),
    ),
    retrieve=extend_schema(
        summary="Get a student interest",
        responses={200: StudentInterestSerializer, 404: NOT_FOUND},
    ),
)
class StudentInterestViewSet(ReadOnlyModelViewSet):
    serializer_class = StudentInterestSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return StudentInterest.objects.select_related(
            "student_profile__user", "interest"
        ).filter(student_profile__user=self.request.user).order_by("pk")
