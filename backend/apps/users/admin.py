from django.contrib import admin

from .models import StudentProfile


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "display_name",
        "college",
        "course",
        "academic_level",
        "contribution_points",
        "onboarding_completed",
        "updated_at",
    )
    list_filter = ("onboarding_completed", "education_background")
    search_fields = ("user__username", "user__email", "display_name", "college")
    list_select_related = ("user", "education_background", "course", "academic_level")
    ordering = ("user__username",)
