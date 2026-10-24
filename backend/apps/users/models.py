from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.education.models import AcademicStageType


class StudentProfile(models.Model):
    """Student-specific public and onboarding data for an authenticated user."""

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="student_profile")
    display_name = models.CharField(max_length=120, blank=True)
    bio = models.TextField(max_length=1000, blank=True)
    # A storage URL/reference keeps profile media out of PostgreSQL and avoids
    # coupling this domain model to a storage provider before Cloudinary.
    avatar_url = models.URLField(blank=True)
    # Internal reference used to clean up replaced Cloudinary media.
    avatar_reference = models.CharField(max_length=255, blank=True)
    contribution_points = models.PositiveIntegerField(default=0)
    college = models.CharField(max_length=120, blank=True)
    country = models.CharField(max_length=120, blank=True)
    state = models.CharField(max_length=120, blank=True)
    city = models.CharField(max_length=120, blank=True)
    education_background = models.ForeignKey(
        "education.EducationBackground", on_delete=models.SET_NULL, null=True, blank=True, related_name="student_profiles"
    )
    custom_background = models.CharField(max_length=120, blank=True)
    course = models.ForeignKey("education.Course", on_delete=models.SET_NULL, null=True, blank=True, related_name="student_profiles")
    custom_course = models.CharField(max_length=160, blank=True)
    academic_level = models.ForeignKey(
        "education.AcademicLevel", on_delete=models.SET_NULL, null=True, blank=True, related_name="student_profiles"
    )
    academic_level_type = models.CharField(
        max_length=16, choices=AcademicStageType.choices, blank=True
    )
    academic_level_value = models.CharField(max_length=120, blank=True)
    onboarding_completed = models.BooleanField(default=False)
    onboarding_completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=["onboarding_completed"])]

    def clean(self):
        errors = {}
        background_is_other = bool(
            self.education_background_id
            and self.education_background
            and (
                self.education_background.slug.casefold() == "other"
                or self.education_background.name.casefold() == "other"
            )
        )
        if self.custom_background and self.education_background_id and not background_is_other:
            errors["custom_background"] = "A custom background requires the Other background option."
        if background_is_other and not self.custom_background:
            errors["custom_background"] = "Enter a custom background when selecting Other."
        if self.custom_background and not self.education_background_id:
            # A custom background is a valid standalone selection.
            pass
        if self.education_background_id and not self.education_background.is_active:
            errors["education_background"] = "Select an active education background."

        course_is_other = bool(
            self.course_id
            and self.course
            and (
                self.course.slug.casefold() == "other"
                or self.course.name.casefold() == "other"
            )
        )
        if self.course and not self.education_background_id:
            errors["education_background"] = "An education background is required when selecting a course."
        if self.course and self.education_background_id and self.course.education_background_id != self.education_background_id:
            errors["course"] = "The selected course must belong to the selected education background."
        if self.course_id and not self.course.is_active:
            errors["course"] = "Select an active course or program."
        if self.custom_course and self.course_id and not course_is_other:
            errors["custom_course"] = "A custom course requires the Other course option."
        if course_is_other and not self.custom_course:
            errors["custom_course"] = "Enter a custom course when selecting Other."
        if self.custom_course and not (self.education_background_id or self.custom_background):
            errors["education_background"] = "A background is required when entering a custom course."
        if self.academic_level and not self.course_id:
            errors["course"] = "A course is required when selecting an academic level."
        if self.academic_level and self.course_id and self.academic_level.course_id != self.course_id:
            errors["academic_level"] = "The selected academic level must belong to the selected course."
        if self.academic_level_id and not self.academic_level.is_active:
            errors["academic_level"] = "Select an active academic level or stage."
        if self.academic_level_id:
            if (
                self.academic_level_type
                and self.academic_level_type != self.academic_level.level_type
            ) or (
                self.academic_level_value
                and self.academic_level_value != self.academic_level.name
            ):
                errors["academic_level_value"] = "Catalog stage type and value must match the selected academic level."
        elif bool(self.academic_level_type) != bool(self.academic_level_value):
            errors["academic_level_value"] = "Academic stage type and value must be provided together."

        has_background = bool(self.education_background_id or self.custom_background)
        has_course = bool(self.course_id or self.custom_course)
        has_stage = bool(self.academic_level_id or (self.academic_level_type and self.academic_level_value))
        if self.onboarding_completed and not (has_background and has_course and has_stage):
            errors["onboarding_completed"] = "Education background, course, and academic level are required before completion."
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return self.display_name or self.user.get_username()


class SignupEmailVerification(models.Model):
    """One-time state for an account that is waiting for email verification."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="signup_email_verification",
    )
    # Signup normalizes this value before saving. Keeping a unique copy makes
    # concurrent pending signups for the same address converge on one record.
    email = models.EmailField(max_length=254, unique=True)
    otp_hash = models.CharField(max_length=128)
    expires_at = models.DateTimeField()
    attempts = models.PositiveSmallIntegerField(default=0)
    last_sent_at = models.DateTimeField(null=True, blank=True)
    # ``last_sent_at`` records broker enqueue time for resend cooldowns. This
    # separate marker records successful email-backend delivery so duplicate
    # task executions can avoid repeating the side effect.
    email_sent_at = models.DateTimeField(null=True, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=["expires_at"])]

    def __str__(self):
        return f"Signup email verification for user {self.user_id}"
