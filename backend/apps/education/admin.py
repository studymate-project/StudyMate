from django.contrib import admin

from .models import AcademicLevel, Course, EducationBackground, Interest, StudentInterest


@admin.register(EducationBackground)
class EducationBackgroundAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("name", "slug")


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("name", "education_background", "slug", "is_active")
    list_filter = ("education_background", "is_active")
    search_fields = ("name", "slug")


@admin.register(AcademicLevel)
class AcademicLevelAdmin(admin.ModelAdmin):
    list_display = ("name", "course", "level_type", "order", "is_active")
    list_filter = ("level_type", "is_active")
    search_fields = ("name", "slug", "course__name")


@admin.register(Interest)
class InterestAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "slug")
    filter_horizontal = ("courses",)


@admin.register(StudentInterest)
class StudentInterestAdmin(admin.ModelAdmin):
    list_display = ("student_profile", "interest", "created_at")
    search_fields = ("student_profile__user__username", "interest__name")
