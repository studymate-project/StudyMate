import logging

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.db.models import Exists, OuterRef, Prefetch
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, extend_schema_view, inline_serializer
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.views import APIView
from rest_framework.mixins import UpdateModelMixin
from rest_framework.viewsets import ReadOnlyModelViewSet

from apps.core.permissions import IsProfileOwnerOrReadOnly
from apps.education.models import StudentInterest
from apps.education.serializers import StudentInterestSerializer
from apps.core.schema import BAD_REQUEST, NOT_FOUND, UNAUTHENTICATED

from .models import StudentProfile
from .serializers import OnboardingSerializer, StudentProfileSerializer
from apps.interactions.models import UserFollow
from apps.notifications.models import Notification
from apps.notifications.services import create_notification


logger = logging.getLogger(__name__)


ONBOARDING_RESPONSE = inline_serializer(
    "OnboardingResponse",
    fields={
        "profile": StudentProfileSerializer(read_only=True),
        "student_interests": StudentInterestSerializer(many=True, read_only=True),
    },
)


class OnboardingView(APIView):
    permission_classes = (IsAuthenticated,)
    throttle_scope = "onboarding_write"

    @extend_schema(
        summary="Submit onboarding choices",
        description="Persist an authenticated user's background, course, academic level, location, and optional course-compatible interests atomically. Ownership and onboarding_completed are server-controlled.",
        request=OnboardingSerializer,
        responses={200: ONBOARDING_RESPONSE, 400: BAD_REQUEST, 401: UNAUTHENTICATED},
    )
    def post(self, request):
        profile = StudentProfile.objects.select_related(
            "user", "education_background", "course", "academic_level"
        ).prefetch_related(
            Prefetch("student_interests", queryset=StudentInterest.objects.select_related("interest"))
        ).filter(user=request.user).first()
        serializer = OnboardingSerializer(
            instance=profile,
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        profile = serializer.save()
        student_interests = profile.student_interests.select_related("interest").order_by("pk")
        return Response(
            {
                "profile": StudentProfileSerializer(profile).data,
                "student_interests": StudentInterestSerializer(student_interests, many=True).data,
            }
        )


@extend_schema_view(
    list=extend_schema(
        summary="List public profiles",
        description="Return paginated profiles. Owner-only onboarding fields are omitted for other users.",
        responses=StudentProfileSerializer(many=True),
    ),
    retrieve=extend_schema(
        summary="Get a public profile",
        description="Look up a profile by the user's username.",
        responses={200: StudentProfileSerializer, 404: NOT_FOUND},
    ),
)
class StudentProfileViewSet(UpdateModelMixin, ReadOnlyModelViewSet):
    """Public profile directory keyed by the user's stable username."""

    serializer_class = StudentProfileSerializer
    permission_classes = (IsProfileOwnerOrReadOnly,)
    lookup_url_kwarg = "identifier"
    queryset = StudentProfile.objects.select_related(
        "user", "education_background", "course", "academic_level"
    ).prefetch_related(
        Prefetch("student_interests", queryset=StudentInterest.objects.select_related("interest"))
    ).order_by("pk")

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.user.is_authenticated:
            queryset = queryset.annotate(
                _is_following=Exists(
                    UserFollow.objects.filter(
                        follower=self.request.user,
                        following_id=OuterRef("user_id"),
                    )
                )
            )
        return queryset

    def get_object(self) -> StudentProfile:
        identifier = self.kwargs[self.lookup_url_kwarg]
        profile = self.get_queryset().filter(user__username=identifier).first()
        if profile:
            self.check_object_permissions(self.request, profile)
            return profile

        # A user can own public content before completing onboarding. Treat
        # that user as a valid public profile instead of making resource and
        # discussion profile links end in a misleading 404.
        user = get_object_or_404(get_user_model(), username=identifier)
        profile, _ = StudentProfile.objects.get_or_create(user=user)
        self.check_object_permissions(self.request, profile)
        return profile

    def get_permissions(self):
        if self.action == "follow":
            return [IsAuthenticated()]
        return super().get_permissions()

    @action(detail=True, methods=("post", "delete"), url_path="follow")
    def follow(self, request, identifier=None):
        target_profile = self.get_object()
        target_user = target_profile.user
        if request.user.pk == target_user.pk:
            raise ValidationError({"detail": "You cannot follow your own profile."})

        relation = UserFollow.objects.filter(
            follower=request.user,
            following=target_user,
        )
        if request.method == "DELETE":
            relation.delete()
            return Response({"is_following": False})

        try:
            with transaction.atomic():
                _, created = UserFollow.objects.get_or_create(
                    follower=request.user,
                    following=target_user,
                )
        except IntegrityError as exc:
            raise ValidationError({"detail": "Unable to follow this profile."}) from exc
        if created:
            try:
                create_notification(
                    recipient=target_user,
                    actor=request.user,
                    notification_type=Notification.NotificationType.NEW_FOLLOWER,
                    related_object=request.user,
                )
            except Exception:
                logger.exception(
                    "Unable to create follower notification follower_id=%s followed_id=%s",
                    request.user.pk,
                    target_user.pk,
                )
        return Response(
            {"is_following": True},
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )
