from django.db import models


class CatalogBase(models.Model):
    """Common fields for active, human-readable education catalog records."""

    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ("name",)

    def __str__(self):
        return self.name


class EducationBackground(CatalogBase):
    """A broad educational context, such as School, Commerce, or Medical."""


class Course(models.Model):
    education_background = models.ForeignKey(EducationBackground, on_delete=models.PROTECT, related_name="courses")
    name = models.CharField(max_length=160)
    slug = models.SlugField(max_length=180)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("name",)
        constraints = [models.UniqueConstraint(fields=["education_background", "slug"], name="unique_course_slug_per_background")]
        indexes = [models.Index(fields=["education_background", "is_active"])]

    def __str__(self):
        return self.name


class AcademicLevel(models.Model):
    class LevelType(models.TextChoices):
        CLASS = "class", "Class"
        SEMESTER = "semester", "Semester"
        YEAR = "year", "Year"
        LEVEL = "level", "Level"
        STAGE = "stage", "Stage"
        OTHER = "other", "Other"

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="academic_levels")
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140)
    level_type = models.CharField(max_length=16, choices=LevelType.choices)
    order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("course", "order", "name")
        constraints = [
            models.UniqueConstraint(fields=["course", "slug"], name="unique_academic_level_slug_per_course"),
            models.UniqueConstraint(fields=["course", "order"], name="unique_academic_level_order_per_course"),
        ]
        indexes = [models.Index(fields=["course", "level_type", "is_active"])]

    def __str__(self):
        return self.name


class Interest(CatalogBase):
    """A topic a student can opt into during onboarding."""

    courses = models.ManyToManyField(Course, related_name="interests", blank=True)


class StudentInterest(models.Model):
    student_profile = models.ForeignKey("users.StudentProfile", on_delete=models.CASCADE, related_name="student_interests")
    interest = models.ForeignKey(Interest, on_delete=models.PROTECT, related_name="student_interests")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["student_profile", "interest"], name="unique_student_interest")]
        indexes = [models.Index(fields=["student_profile", "created_at"])]

    def __str__(self):
        return f"{self.student_profile} — {self.interest}"
