from django.contrib import admin

from .models import Answer, Question


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("title", "author", "subject", "topic", "academic_level", "status", "created_at")
    list_filter = ("status", "subject", "academic_level")
    search_fields = ("title", "slug", "body", "author__username", "subject", "topic")
    list_select_related = ("author", "academic_level")
    prepopulated_fields = {"slug": ("title",)}


@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ("question", "author", "is_helpful", "status", "created_at")
    list_filter = ("is_helpful", "status")
    search_fields = ("body", "question__title", "author__username")
    list_select_related = ("question", "author")
