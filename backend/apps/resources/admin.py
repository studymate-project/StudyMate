from django.contrib import admin

from .models import Resource, ResourceDownload, ResourceView, Tag, Video


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "created_at")
    search_fields = ("name", "slug")


@admin.register(Resource)
class ResourceAdmin(admin.ModelAdmin):
    list_display = ("title", "resource_type", "uploader", "subject", "academic_level", "status", "created_at")
    list_filter = ("resource_type", "status", "difficulty")
    search_fields = ("title", "slug", "subject", "topic", "uploader__username")
    list_select_related = ("uploader", "academic_level")
    prepopulated_fields = {"slug": ("title",)}


@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    list_display = ("title", "uploader", "youtube_video_id", "subject", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("title", "slug", "youtube_video_id", "subject", "topic", "uploader__username")
    list_select_related = ("uploader", "academic_level")
    prepopulated_fields = {"slug": ("title",)}


@admin.register(ResourceView)
class ResourceViewAdmin(admin.ModelAdmin):
    list_display = ("resource", "user", "viewed_at")
    list_select_related = ("resource", "user")


@admin.register(ResourceDownload)
class ResourceDownloadAdmin(admin.ModelAdmin):
    list_display = ("resource", "user", "downloaded_at")
    list_select_related = ("resource", "user")
