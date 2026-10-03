from django.contrib import admin

from .models import AnswerUpvote, QuestionUpvote, ResourceUpvote, SavedResource, UserFollow


class UserTargetAdmin(admin.ModelAdmin):
    list_display = ("user", "created_at")
    list_select_related = ("user",)


@admin.register(SavedResource)
class SavedResourceAdmin(UserTargetAdmin):
    list_display = ("user", "resource", "created_at")
    search_fields = ("user__username", "resource__title")
    list_select_related = ("user", "resource")


@admin.register(ResourceUpvote)
class ResourceUpvoteAdmin(UserTargetAdmin):
    list_display = ("user", "resource", "created_at")
    search_fields = ("user__username", "resource__title")
    list_select_related = ("user", "resource")


@admin.register(QuestionUpvote)
class QuestionUpvoteAdmin(UserTargetAdmin):
    list_display = ("user", "question", "created_at")
    search_fields = ("user__username", "question__title")
    list_select_related = ("user", "question")


@admin.register(AnswerUpvote)
class AnswerUpvoteAdmin(UserTargetAdmin):
    list_display = ("user", "answer", "created_at")
    search_fields = ("user__username", "answer__body")
    list_select_related = ("user", "answer")


@admin.register(UserFollow)
class UserFollowAdmin(admin.ModelAdmin):
    list_display = ("follower", "following", "created_at")
    search_fields = ("follower__username", "following__username")
    list_select_related = ("follower", "following")
