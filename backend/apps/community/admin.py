from django.contrib import admin

from .models import Answer, DiscussionComment, DiscussionCommentLike, Question


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


@admin.register(DiscussionComment)
class DiscussionCommentAdmin(admin.ModelAdmin):
    list_display = ("body", "author", "resource", "video", "parent", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("body", "author__username", "resource__title", "video__title")
    list_select_related = ("author", "resource", "video", "parent")


@admin.register(DiscussionCommentLike)
class DiscussionCommentLikeAdmin(admin.ModelAdmin):
    list_display = ("comment", "user", "created_at")
    search_fields = ("comment__body", "user__username")
    list_select_related = ("comment", "user")
