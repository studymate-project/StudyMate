from rest_framework import serializers

from .models import AcademicLevel, Course, EducationBackground, Interest, StudentInterest


class EducationBackgroundSerializer(serializers.ModelSerializer):
    class Meta:
        model = EducationBackground
        fields = ("id", "name", "slug", "description", "is_active", "created_at", "updated_at")
        read_only_fields = ("id", "created_at", "updated_at")


class CourseSerializer(serializers.ModelSerializer):
    education_background_detail = EducationBackgroundSerializer(
        source="education_background", read_only=True
    )

    class Meta:
        model = Course
        fields = (
            "id",
            "name",
            "slug",
            "description",
            "is_active",
            "education_background",
            "education_background_detail",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "education_background_detail", "created_at", "updated_at")


class AcademicLevelSerializer(serializers.ModelSerializer):
    course_detail = CourseSerializer(source="course", read_only=True)

    class Meta:
        model = AcademicLevel
        fields = (
            "id",
            "name",
            "slug",
            "level_type",
            "order",
            "is_active",
            "course",
            "course_detail",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "course_detail", "created_at", "updated_at")


class InterestSerializer(serializers.ModelSerializer):
    class Meta:
        model = Interest
        fields = ("id", "name", "slug", "description", "is_active", "created_at", "updated_at")
        read_only_fields = ("id", "created_at", "updated_at")


class StudentInterestSerializer(serializers.ModelSerializer):
    interest_detail = InterestSerializer(source="interest", read_only=True)

    class Meta:
        model = StudentInterest
        fields = ("id", "student_profile", "interest", "interest_detail", "created_at")
        read_only_fields = ("id", "student_profile", "interest_detail", "created_at")
