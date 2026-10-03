from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models import Q
from django.core.validators import URLValidator
from django.utils import timezone
from django.utils.text import slugify
from urllib.parse import urlsplit
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed

from apps.education.models import AcademicLevel, Course, EducationBackground, Interest, StudentInterest
from apps.interactions.models import UserFollow

from .models import StudentProfile
from .avatar_validation import AvatarValidationError, validate_avatar_file
from apps.resources.services.cloudinary import (
    CloudinaryUploadError,
    discard_cloudinary_avatar_reference,
    discard_uploaded_avatar,
    upload_profile_avatar,
)


User = get_user_model()


class PublicUserSerializer(serializers.ModelSerializer):
    """Safe identity summary for relationships in API responses."""

    class Meta:
        model = User
        fields = ("id", "username", "first_name", "last_name")
        read_only_fields = fields


class StudentProfileSerializer(serializers.ModelSerializer):
    user = PublicUserSerializer(read_only=True)
    is_following = serializers.SerializerMethodField()
    avatar_file = serializers.FileField(write_only=True, required=False, allow_null=True)

    class Meta:
        model = StudentProfile
        fields = (
            "id",
            "user",
            "is_following",
            "display_name",
            "bio",
            "avatar_url",
            "avatar_file",
            "contribution_points",
            "college",
            "education_background",
            "course",
            "academic_level",
            "onboarding_completed",
            "onboarding_completed_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "user",
            "contribution_points",
            "onboarding_completed",
            "onboarding_completed_at",
            "created_at",
            "updated_at",
        )

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get("request")
        if request is not None:
            is_owner = request.user.is_authenticated and request.user.pk == instance.user_id
            if not is_owner:
                data.pop("onboarding_completed", None)
                data.pop("onboarding_completed_at", None)
        return data

    def get_is_following(self, instance) -> bool:
        request = self.context.get("request")
        if request is None or not request.user.is_authenticated:
            return False
        return UserFollow.objects.filter(
            follower=request.user,
            following=instance.user,
        ).exists()

    def validate(self, attrs: dict[str, object]) -> dict[str, object]:
        profile = self.instance if isinstance(self.instance, StudentProfile) else None
        background = attrs.get("education_background", profile.education_background if profile else None)
        course = attrs.get("course", profile.course if profile else None)
        academic_level = attrs.get("academic_level", profile.academic_level if profile else None)
        onboarding_completed = attrs.get(
            "onboarding_completed", profile.onboarding_completed if profile else False
        )

        avatar_file = attrs.get("avatar_file") if "avatar_file" in attrs else None
        avatar_url = attrs.get("avatar_url") if "avatar_url" in attrs else None
        if avatar_file and avatar_url:
            raise serializers.ValidationError(
                {"avatar_url": "Choose an uploaded image or an image URL, not both."}
            )
        if avatar_file:
            try:
                validate_avatar_file(avatar_file)
            except AvatarValidationError as error:
                raise serializers.ValidationError({"avatar_file": str(error)}) from error
        if "avatar_url" in attrs and avatar_url:
            try:
                URLValidator(schemes={"https"})(avatar_url)
                parsed_url = urlsplit(avatar_url)
                if parsed_url.username or parsed_url.password or not parsed_url.hostname:
                    raise DjangoValidationError("Avatar URLs may not contain credentials.")
            except DjangoValidationError as error:
                raise serializers.ValidationError(
                    {"avatar_url": "Enter a valid HTTPS image URL."}
                ) from error

        for field_name, value in (
            ("education_background", background),
            ("course", course),
            ("academic_level", academic_level),
        ):
            if field_name in attrs and value is not None and not value.is_active:
                raise serializers.ValidationError(
                    {field_name: "Select an active education option."}
                )

        if course is not None and background is None:
            raise serializers.ValidationError(
                {"education_background": "An education background is required when selecting a course."}
            )
        if course is not None and background is not None and course.education_background_id != background.pk:
            raise serializers.ValidationError(
                {"course": "The selected course must belong to the selected education background."}
            )
        if academic_level is not None and course is None:
            raise serializers.ValidationError({"course": "A course is required when selecting an academic level."})
        if academic_level is not None and course is not None and academic_level.course_id != course.pk:
            raise serializers.ValidationError(
                {"academic_level": "The selected academic level must belong to the selected course."}
            )
        if onboarding_completed and not (background and course and academic_level):
            raise serializers.ValidationError(
                {
                    "onboarding_completed": (
                        "Education background, course, and academic level are required before completion."
                    )
                }
            )
        return attrs

    def update(self, instance, validated_data):
        submitted_avatar = validated_data.pop("avatar_file", None)
        old_reference = instance.avatar_reference or None
        upload_result = None

        if submitted_avatar:
            try:
                upload_result = upload_profile_avatar(
                    validated_file=submitted_avatar,
                    uploader_id=instance.user_id,
                )
            except CloudinaryUploadError as error:
                raise serializers.ValidationError({"avatar_file": str(error)}) from error
            validated_data["avatar_url"] = upload_result.secure_url
            validated_data["avatar_reference"] = upload_result.reference
        elif "avatar_url" in validated_data and validated_data["avatar_url"] != instance.avatar_url:
            validated_data["avatar_reference"] = ""

        try:
            with transaction.atomic():
                for field_name, value in validated_data.items():
                    setattr(instance, field_name, value)
                instance.full_clean()
                instance.save()
                if old_reference and old_reference != instance.avatar_reference:
                    transaction.on_commit(
                        lambda: discard_cloudinary_avatar_reference(
                            old_reference,
                            excluding_profile_id=instance.pk,
                        )
                    )
            return instance
        except Exception:
            discard_uploaded_avatar(upload_result)
            raise


class OnboardingSerializer(serializers.Serializer):
    """Validate and persist one authenticated user's final onboarding choice."""

    education_background = serializers.IntegerField(min_value=1)
    course = serializers.IntegerField(min_value=1)
    academic_level = serializers.IntegerField(min_value=1)
    interests = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        allow_empty=False,
        max_length=8,
    )

    _protected_fields = {
        "user",
        "user_id",
        "username",
        "profile",
        "profile_id",
        "onboarding_completed",
        "onboarding_completed_at",
    }

    def validate(self, attrs):
        supplied_protected_fields = self._protected_fields.intersection(self.initial_data.keys())
        if supplied_protected_fields:
            raise serializers.ValidationError(
                {
                    field: "This field is controlled by the authenticated request."
                    for field in sorted(supplied_protected_fields)
                }
            )

        background = EducationBackground.objects.filter(
            pk=attrs["education_background"], is_active=True
        ).first()
        if background is None:
            raise serializers.ValidationError(
                {"education_background": "Select a valid education background."}
            )

        course = Course.objects.select_related("education_background").filter(
            pk=attrs["course"],
            is_active=True,
            education_background__is_active=True,
        ).first()
        if course is None:
            raise serializers.ValidationError({"course": "Select a valid course."})
        if course.education_background_id != background.pk:
            raise serializers.ValidationError(
                {"course": "The selected course must belong to the selected education background."}
            )

        academic_level = AcademicLevel.objects.select_related(
            "course", "course__education_background"
        ).filter(
            pk=attrs["academic_level"],
            is_active=True,
            course__is_active=True,
            course__education_background__is_active=True,
        ).first()
        if academic_level is None:
            raise serializers.ValidationError({"academic_level": "Select a valid academic level."})
        if academic_level.course_id != course.pk:
            raise serializers.ValidationError(
                {"academic_level": "The selected academic level must belong to the selected course."}
            )

        interest_ids = attrs["interests"]
        if len(interest_ids) != len(set(interest_ids)):
            raise serializers.ValidationError(
                {"interests": "Each interest may only be selected once."}
            )

        selected_interests = list(
            Interest.objects.filter(pk__in=interest_ids, is_active=True)
        )
        selected_by_id = {interest.pk: interest for interest in selected_interests}
        missing_ids = [interest_id for interest_id in interest_ids if interest_id not in selected_by_id]
        if missing_ids:
            raise serializers.ValidationError(
                {"interests": "Select valid interests from the education catalog."}
            )

        valid_interest_ids = set(
            Interest.objects.filter(
                pk__in=interest_ids,
                is_active=True,
                courses=course,
            ).values_list("pk", flat=True)
        )
        if valid_interest_ids != set(interest_ids):
            raise serializers.ValidationError(
                {"interests": "All selected interests must be valid for the selected course."}
            )

        attrs["education_background"] = background
        attrs["course"] = course
        attrs["academic_level"] = academic_level
        attrs["interests"] = [selected_by_id[interest_id] for interest_id in interest_ids]
        return attrs

    def _save_profile(self, profile, validated_data):
        user = self.context["request"].user
        if profile is None:
            profile = StudentProfile(user=user)

        was_completed = profile.onboarding_completed
        profile.education_background = validated_data["education_background"]
        profile.course = validated_data["course"]
        profile.academic_level = validated_data["academic_level"]
        profile.onboarding_completed = True
        if not was_completed or profile.onboarding_completed_at is None:
            profile.onboarding_completed_at = timezone.now()

        profile.full_clean()
        profile.save()
        StudentInterest.objects.filter(student_profile=profile).delete()
        StudentInterest.objects.bulk_create(
            [
                StudentInterest(student_profile=profile, interest=interest)
                for interest in validated_data["interests"]
            ]
        )
        return profile

    @transaction.atomic
    def create(self, validated_data):
        return self._save_profile(None, validated_data)

    @transaction.atomic
    def update(self, instance, validated_data):
        return self._save_profile(instance, validated_data)


class RegistrationSerializer(serializers.Serializer):
    """Create a Django user and its initial student profile atomically.

    The public signup contract uses human-readable education values. They are
    resolved to existing catalog rows; no client-controlled ownership or user
    fields are accepted.
    """

    name = serializers.CharField(max_length=120, write_only=True)
    email = serializers.EmailField(write_only=True)
    password = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
        style={"input_type": "password"},
    )
    college = serializers.CharField(max_length=120, write_only=True)
    course = serializers.CharField(max_length=160, write_only=True)
    semester = serializers.CharField(max_length=120, write_only=True)

    @staticmethod
    def _split_name(name: str) -> tuple[str, str]:
        parts = name.strip().split(None, 1)
        return parts[0], parts[1] if len(parts) == 2 else ""

    @staticmethod
    def _username_base(email: str) -> str:
        local_part = email.rsplit("@", 1)[0]
        return (slugify(local_part) or "student")[:150]

    @classmethod
    def _unique_username(cls, email: str) -> str:
        base = cls._username_base(email)
        candidate = base
        suffix = 2
        while User.objects.filter(username=candidate).exists():
            suffix_text = f"-{suffix}"
            candidate = f"{base[:150 - len(suffix_text)]}{suffix_text}"
            suffix += 1
        return candidate

    @staticmethod
    def _resolve_catalog_value(queryset, value: str, field_name: str):
        matches = list(
            queryset.filter(Q(name__iexact=value) | Q(slug__iexact=value)).order_by("pk")[:2]
        )
        if not matches:
            raise serializers.ValidationError(
                {field_name: "Select a valid value from the education catalog."}
            )
        if len(matches) > 1:
            raise serializers.ValidationError(
                {field_name: "The selected education value is ambiguous."}
            )
        return matches[0]

    def validate(self, attrs):
        name = attrs["name"].strip()
        if not name:
            raise serializers.ValidationError({"name": "This field may not be blank."})

        email = attrs["email"].strip().casefold()
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError({"email": "A user with this email already exists."})

        first_name, _ = self._split_name(name)
        prospective_user = User(
            username=self._unique_username(email),
            email=email,
            first_name=first_name,
        )
        try:
            validate_password(attrs["password"], user=prospective_user)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"password": list(exc.messages)}) from exc

        college = attrs["college"].strip()
        course_name = attrs["course"].strip()
        semester = attrs["semester"].strip()
        if not college:
            raise serializers.ValidationError({"college": "This field may not be blank."})
        if not course_name:
            raise serializers.ValidationError({"course": "This field may not be blank."})
        if not semester:
            raise serializers.ValidationError({"semester": "This field may not be blank."})

        # College/university is user-provided profile data. It is not the same
        # thing as an EducationBackground catalog row (for example,
        # "Engineering"), so it must not be resolved against that catalog.
        course = self._resolve_catalog_value(
            Course.objects.filter(
                is_active=True,
                education_background__is_active=True,
            ),
            course_name,
            "course",
        )
        background = course.education_background
        academic_level = self._resolve_catalog_value(
            AcademicLevel.objects.filter(course=course, is_active=True), semester, "semester"
        )

        attrs["name"] = name
        attrs["email"] = email
        attrs["_education_background"] = background
        attrs["_course"] = course
        attrs["_academic_level"] = academic_level
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        background = validated_data.pop("_education_background")
        course = validated_data.pop("_course")
        academic_level = validated_data.pop("_academic_level")
        name = validated_data.pop("name")
        email = validated_data.pop("email")
        password = validated_data.pop("password")
        college = validated_data.pop("college")
        first_name, last_name = self._split_name(name)

        user = User.objects.create_user(
            username=self._unique_username(email),
            email=email,
            first_name=first_name,
            last_name=last_name,
            password=password,
        )
        StudentProfile.objects.create(
            user=user,
            display_name=name,
            college=college,
            education_background=background,
            course=course,
            academic_level=academic_level,
        )
        return user

    def to_representation(self, instance):
        user_data = PublicUserSerializer(instance).data
        user_data["email"] = instance.email
        return {
            "user": user_data,
            "profile": StudentProfileSerializer(instance.student_profile).data,
        }


class LoginSerializer(serializers.Serializer):
    """Validate email credentials using Django's configured auth backend."""

    email = serializers.EmailField(write_only=True)
    password = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
        style={"input_type": "password"},
    )

    def validate(self, attrs):
        email = attrs["email"].strip().casefold()
        password = attrs["password"]
        request = self.context.get("request")
        user = User.objects.filter(email__iexact=email).first()
        login_identifier = user.username if user is not None else email
        authenticated_user = authenticate(
            request=request,
            username=login_identifier,
            password=password,
        )
        if authenticated_user is None:
            raise AuthenticationFailed("Invalid email or password.")
        attrs["user"] = authenticated_user
        return attrs
