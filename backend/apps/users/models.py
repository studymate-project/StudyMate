from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


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
    education_background = models.ForeignKey(
        "education.EducationBackground", on_delete=models.SET_NULL, null=True, blank=True, related_name="student_profiles"
    )
    course = models.ForeignKey("education.Course", on_delete=models.SET_NULL, null=True, blank=True, related_name="student_profiles")
    academic_level = models.ForeignKey(
        "education.AcademicLevel", on_delete=models.SET_NULL, null=True, blank=True, related_name="student_profiles"
    )
    onboarding_completed = models.BooleanField(default=False)
    onboarding_completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=["onboarding_completed"])]

    def clean(self):
        errors = {}
        if self.course and not self.education_background_id:
            errors["education_background"] = "An education background is required when selecting a course."
        if self.course and self.education_background_id and self.course.education_background_id != self.education_background_id:
            errors["course"] = "The selected course must belong to the selected education background."
        if self.academic_level and not self.course_id:
            errors["course"] = "A course is required when selecting an academic level."
        if self.academic_level and self.course_id and self.academic_level.course_id != self.course_id:
            errors["academic_level"] = "The selected academic level must belong to the selected course."
        if self.onboarding_completed and not (self.education_background and self.course and self.academic_level):
            errors["onboarding_completed"] = "Education background, course, and academic level are required before completion."
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return self.display_name or self.user.get_username()
