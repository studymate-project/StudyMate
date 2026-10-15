from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.core.validators import URLValidator
from django.utils import timezone
from django.utils.text import slugify
from urllib.parse import urlsplit
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from drf_spectacular.utils import extend_schema_field

from apps.education.models import (
    AcademicLevel,
    AcademicStageType,
    Course,
    EducationBackground,
    Interest,
    StudentInterest,
)
from apps.education.serializers import InterestSerializer as CatalogInterestSerializer
from apps.interactions.models import UserFollow

from .models import StudentProfile
from .services.verification import create_signup_verification
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
    interests = serializers.SerializerMethodField()
    interest_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        write_only=True,
        required=False,
        allow_empty=True,
        max_length=8,
    )
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
            "country",
            "state",
            "city",
            "education_background",
            "custom_background",
            "course",
            "custom_course",
            "academic_level",
            "academic_level_type",
            "academic_level_value",
            "interests",
            "interest_ids",
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
        if hasattr(instance, "_is_following"):
            return bool(instance._is_following)
        request = self.context.get("request")
        if request is None or not request.user.is_authenticated:
            return False
        return UserFollow.objects.filter(
            follower=request.user,
            following=instance.user,
        ).exists()

    @extend_schema_field(CatalogInterestSerializer(many=True))
    def get_interests(self, instance):
        if "student_interests" in getattr(instance, "_prefetched_objects_cache", {}):
            student_interests = instance.student_interests.all()
        else:
            student_interests = instance.student_interests.select_related("interest").all()
        return [
            {
                "id": student_interest.interest_id,
                "name": student_interest.interest.name,
                "slug": student_interest.interest.slug,
                "description": student_interest.interest.description,
            }
            for student_interest in student_interests
        ]

    def validate(self, attrs: dict[str, object]) -> dict[str, object]:
        profile = self.instance if isinstance(self.instance, StudentProfile) else None
        background = attrs.get("education_background", profile.education_background if profile else None)
        custom_background = attrs.get(
            "custom_background", profile.custom_background if profile else ""
        )
        course = attrs.get("course", profile.course if profile else None)
        custom_course = attrs.get("custom_course", profile.custom_course if profile else "")
        academic_level = attrs.get("academic_level", profile.academic_level if profile else None)
        custom_stage_type = attrs.get(
            "academic_level_type", profile.academic_level_type if profile else ""
        )
        custom_stage_value = attrs.get(
            "academic_level_value", profile.academic_level_value if profile else ""
        )
        custom_stage_was_submitted = (
            "academic_level_type" in attrs or "academic_level_value" in attrs
        )
        onboarding_completed = attrs.get(
            "onboarding_completed", profile.onboarding_completed if profile else False
        )

        if "interest_ids" in attrs:
            interest_ids = attrs.pop("interest_ids")
            if len(interest_ids) != len(set(interest_ids)):
                raise serializers.ValidationError(
                    {"interest_ids": "Each interest may only be selected once."}
                )

            selected_interests = list(
                Interest.objects.filter(pk__in=interest_ids, is_active=True)
            )
            selected_by_id = {interest.pk: interest for interest in selected_interests}
            if len(selected_by_id) != len(interest_ids):
                raise serializers.ValidationError(
                    {"interest_ids": "Select valid interests from the education catalog."}
                )

            if course:
                valid_interest_ids = set(
                    Interest.objects.filter(
                        pk__in=interest_ids,
                        is_active=True,
                        courses=course,
                    ).values_list("pk", flat=True)
                )
                if valid_interest_ids != set(interest_ids):
                    raise serializers.ValidationError(
                        {"interest_ids": "All selected interests must be valid for the selected course."}
                    )
            attrs["selected_interests"] = [
                selected_by_id[interest_id] for interest_id in interest_ids
            ]

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

        background_is_other = bool(
            background
            and (
                background.slug.casefold() == "other"
                or background.name.casefold() == "other"
            )
        )
        if custom_background and background and not background_is_other:
            raise serializers.ValidationError(
                {"custom_background": "A custom background requires the Other background option."}
            )
        if background_is_other and not custom_background:
            raise serializers.ValidationError(
                {"custom_background": "Enter a custom background when selecting Other."}
            )

        course_is_other = bool(
            course
            and (course.slug.casefold() == "other" or course.name.casefold() == "other")
        )
        if custom_course and course and not course_is_other:
            raise serializers.ValidationError(
                {"custom_course": "A custom course requires the Other course option."}
            )
        if course_is_other and not custom_course:
            raise serializers.ValidationError(
                {"custom_course": "Enter a custom course when selecting Other."}
            )
        if custom_course and not (background or custom_background):
            raise serializers.ValidationError(
                {"education_background": "A background is required when entering a custom course."}
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
        if custom_stage_was_submitted and bool(custom_stage_type) != bool(custom_stage_value):
            raise serializers.ValidationError(
                {"academic_level_value": "Academic stage type and value must be provided together."}
            )
        if academic_level is not None and custom_stage_was_submitted:
            raise serializers.ValidationError(
                {"academic_level_value": "Use either a catalog stage or a custom academic stage, not both."}
            )
        if onboarding_completed and not (background and course and academic_level):
            if not (background or custom_background) or not (course or custom_course) or not (
                academic_level or (custom_stage_type and custom_stage_value)
            ):
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
        selected_interests = validated_data.pop("selected_interests", None)
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

        selected_level = validated_data.get("academic_level")
        if selected_level is not None:
            validated_data["academic_level_type"] = selected_level.level_type
            validated_data["academic_level_value"] = selected_level.name
        elif "academic_level" in validated_data:
            validated_data["academic_level"] = None
            validated_data["academic_level_type"] = validated_data.get("academic_level_type", "")
            validated_data["academic_level_value"] = validated_data.get("academic_level_value", "")

        try:
            with transaction.atomic():
                for field_name, value in validated_data.items():
                    setattr(instance, field_name, value)
                instance.full_clean()
                instance.save()
                if selected_interests is not None:
                    StudentInterest.objects.filter(student_profile=instance).delete()
                    StudentInterest.objects.bulk_create(
                        [
                            StudentInterest(
                                student_profile=instance,
                                interest=interest,
                            )
                            for interest in selected_interests
                        ]
                    )
                    getattr(instance, "_prefetched_objects_cache", {}).pop(
                        "student_interests", None
                    )
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

    education_background = serializers.IntegerField(min_value=1, required=False, allow_null=True)
    custom_background = serializers.CharField(max_length=120, required=False, allow_blank=True)
    course = serializers.IntegerField(min_value=1, required=False, allow_null=True)
    custom_course = serializers.CharField(max_length=160, required=False, allow_blank=True)
    academic_level = serializers.IntegerField(min_value=1, required=False, allow_null=True)
    academic_level_type = serializers.ChoiceField(
        choices=AcademicStageType.choices, required=False, allow_blank=True
    )
    academic_level_value = serializers.CharField(max_length=120, required=False, allow_blank=True)
    country = serializers.CharField(max_length=120, required=False, allow_blank=True)
    state = serializers.CharField(max_length=120, required=False, allow_blank=True)
    city = serializers.CharField(max_length=120, required=False, allow_blank=True)
    interests = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        required=False,
        allow_empty=True,
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

        background_id = attrs.get("education_background")
        custom_background = attrs.get("custom_background", "").strip()
        background = None
        if background_id is not None:
            background = EducationBackground.objects.filter(
                pk=background_id, is_active=True
            ).first()
            if background is None:
                raise serializers.ValidationError(
                    {"education_background": "Select a valid education background."}
                )

        background_is_other = bool(
            background
            and (
                background.slug.casefold() == "other"
                or background.name.casefold() == "other"
            )
        )
        if background_is_other and not custom_background:
            raise serializers.ValidationError(
                {"custom_background": "Enter a custom background when selecting Other."}
            )
        if custom_background and background and not background_is_other:
            raise serializers.ValidationError(
                {"custom_background": "A custom background requires the Other background option."}
            )
        if not background and not custom_background:
            raise serializers.ValidationError(
                {"education_background": "Select an education background or enter a custom background."}
            )

        course_id = attrs.get("course")
        custom_course = attrs.get("custom_course", "").strip()
        course = None
        if course_id is not None:
            course = Course.objects.select_related("education_background").filter(
                pk=course_id,
                is_active=True,
                education_background__is_active=True,
            ).first()
            if course is None:
                raise serializers.ValidationError({"course": "Select a valid course or program."})
            if background and course.education_background_id != background.pk:
                raise serializers.ValidationError(
                    {"course": "The selected course must belong to the selected education background."}
                )
        course_is_other = bool(
            course
            and (course.slug.casefold() == "other" or course.name.casefold() == "other")
        )
        if course_is_other and not custom_course:
            raise serializers.ValidationError(
                {"custom_course": "Enter a custom course or program when selecting Other."}
            )
        if custom_course and course and not course_is_other:
            raise serializers.ValidationError(
                {"custom_course": "A custom course requires the Other course option."}
            )
        if not course and not custom_course:
            raise serializers.ValidationError(
                {"course": "Select a course or program, or enter a custom course."}
            )

        academic_level_id = attrs.get("academic_level")
        academic_level = None
        if academic_level_id is not None:
            academic_level = AcademicLevel.objects.select_related(
                "course", "course__education_background"
            ).filter(
                pk=academic_level_id,
                is_active=True,
                course__is_active=True,
                course__education_background__is_active=True,
            ).first()
            if academic_level is None:
                raise serializers.ValidationError({"academic_level": "Select a valid academic level or stage."})
            if not course:
                raise serializers.ValidationError(
                    {"academic_level": "A catalog academic level requires a catalog course or program."}
                )
            if academic_level.course_id != course.pk:
                raise serializers.ValidationError(
                    {"academic_level": "The selected academic level must belong to the selected course."}
                )

        custom_stage_type = attrs.get("academic_level_type", "")
        custom_stage_value = attrs.get("academic_level_value", "").strip()
        if bool(custom_stage_type) != bool(custom_stage_value):
            raise serializers.ValidationError(
                {"academic_level_value": "Academic stage type and value must be provided together."}
            )
        if academic_level and (custom_stage_type or custom_stage_value):
            raise serializers.ValidationError(
                {"academic_level_value": "Use either a catalog stage or a custom academic stage, not both."}
            )
        if not academic_level and not (custom_stage_type and custom_stage_value):
            raise serializers.ValidationError(
                {"academic_level": "Select an academic level or provide a custom academic stage."}
            )

        interest_ids = attrs.get("interests")
        if interest_ids is not None:
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

            if course:
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
            attrs["interests"] = [selected_by_id[interest_id] for interest_id in interest_ids]

        attrs["education_background"] = background
        attrs["custom_background"] = custom_background
        attrs["course"] = course
        attrs["custom_course"] = custom_course
        attrs["academic_level"] = academic_level
        attrs["academic_level_type"] = custom_stage_type
        attrs["academic_level_value"] = custom_stage_value
        return attrs

    def _save_profile(self, profile, validated_data):
        user = self.context["request"].user
        if profile is None:
            profile = StudentProfile(user=user)

        was_completed = profile.onboarding_completed
        profile.education_background = validated_data["education_background"]
        profile.custom_background = validated_data.get("custom_background", profile.custom_background)
        profile.course = validated_data["course"]
        profile.custom_course = validated_data.get("custom_course", profile.custom_course)
        profile.academic_level = validated_data["academic_level"]
        if profile.academic_level is not None:
            profile.academic_level_type = profile.academic_level.level_type
            profile.academic_level_value = profile.academic_level.name
        else:
            profile.academic_level_type = validated_data.get("academic_level_type", "")
            profile.academic_level_value = validated_data.get("academic_level_value", "")
        for field_name in ("country", "state", "city"):
            if field_name in validated_data:
                setattr(profile, field_name, validated_data[field_name].strip())
        profile.onboarding_completed = True
        if not was_completed or profile.onboarding_completed_at is None:
            profile.onboarding_completed_at = timezone.now()

        profile.full_clean()
        profile.save()
        if "interests" in validated_data:
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

    Signup creates identity and location data only. Education selections belong
    to onboarding so users are not forced into a semester-based flow.
    """

    name = serializers.CharField(max_length=120, write_only=True)
    email = serializers.EmailField(write_only=True)
    password = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
        style={"input_type": "password"},
    )
    college = serializers.CharField(max_length=120, write_only=True, required=False, allow_blank=True)
    country = serializers.CharField(max_length=120, write_only=True, required=False, allow_blank=True)
    state = serializers.CharField(max_length=120, write_only=True, required=False, allow_blank=True)
    city = serializers.CharField(max_length=120, write_only=True, required=False, allow_blank=True)

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

        attrs["name"] = name
        attrs["email"] = email
        for field_name in ("college", "country", "state", "city"):
            attrs[field_name] = attrs.get(field_name, "").strip()
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        name = validated_data.pop("name")
        email = validated_data.pop("email")
        password = validated_data.pop("password")
        first_name, last_name = self._split_name(name)

        user = User(
            username=self._unique_username(email),
            email=email,
            first_name=first_name,
            last_name=last_name,
            is_active=False,
        )
        user.set_password(password)
        user.save()
        StudentProfile.objects.create(
            user=user,
            display_name=name,
            **validated_data,
        )
        create_signup_verification(user=user)
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


class SignupVerificationRequestSerializer(serializers.Serializer):
    email = serializers.EmailField(write_only=True)

    def validate_email(self, value):
        return value.strip().casefold()


class SignupVerificationVerifySerializer(serializers.Serializer):
    email = serializers.EmailField(write_only=True)
    code = serializers.CharField(write_only=True, trim_whitespace=False, max_length=32)

    def validate_email(self, value):
        return value.strip().casefold()
