from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from rest_framework import serializers
from uuid import UUID

from apps.education.models import AcademicLevel
from apps.users.serializers import PublicUserSerializer

from .models import Resource, Tag, Video
from .file_validation import ResourceFileValidationError, validate_resource_file
from .services.cloudinary import (
    CloudinaryUploadError,
    CloudinaryUploadResult,
    cloudinary_reference_url,
    discard_cloudinary_reference,
    discard_uploaded_resource,
    is_cloudinary_reference,
    upload_resource_file,
)
from .youtube import normalize_youtube_video_id


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ("id", "name", "slug", "created_at")
        read_only_fields = ("id", "created_at")


class ResourceSerializer(serializers.ModelSerializer):
    uploader = PublicUserSerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    views = serializers.SerializerMethodField()
    downloads = serializers.SerializerMethodField()
    saves = serializers.SerializerMethodField()
    upvotes = serializers.SerializerMethodField()
    is_saved = serializers.SerializerMethodField()
    tag_ids = serializers.PrimaryKeyRelatedField(
        source="tags", many=True, queryset=Tag.objects.all(), write_only=True, required=False
    )

    class Meta:
        model = Resource
        fields = (
            "id",
            "title",
            "slug",
            "description",
            "uploader",
            "subject",
            "topic",
            "course",
            "semester",
            "academic_level",
            "resource_type",
            "file",
            "external_url",
            "tags",
            "tag_ids",
            "difficulty",
            "status",
            "created_at",
            "updated_at",
            "views",
            "downloads",
            "saves",
            "upvotes",
            "is_saved",
        )
        read_only_fields = ("id", "slug", "uploader", "status", "created_at", "updated_at")

    @staticmethod
    def _count(instance, annotation_name, related_name):
        annotated_count = getattr(instance, annotation_name, None)
        return annotated_count if annotated_count is not None else getattr(instance, related_name).count()

    def get_views(self, instance):
        return self._count(instance, "_view_count", "view_events")

    def get_downloads(self, instance):
        return self._count(instance, "_download_count", "download_events")

    def get_saves(self, instance):
        return self._count(instance, "_save_count", "saved_by")

    def get_upvotes(self, instance):
        return self._count(instance, "_upvote_count", "upvotes")

    def get_is_saved(self, instance):
        if hasattr(instance, "_is_saved"):
            return bool(instance._is_saved)
        request = self.context.get("request")
        return bool(
            request
            and request.user.is_authenticated
            and instance.saved_by.filter(user=request.user).exists()
        )

    def validate(self, attrs: dict[str, object]) -> dict[str, object]:
        resource = self.instance if isinstance(self.instance, Resource) else None
        resource_type = attrs.get("resource_type", resource.resource_type if resource else None)
        external_url = attrs.get("external_url", resource.external_url if resource else None)
        submitted_file = attrs.get("file") if "file" in attrs else None
        errors = {}
        if resource_type == Resource.ResourceType.LINK and not external_url:
            errors["external_url"] = "A link resource requires an external URL."
        if resource_type == Resource.ResourceType.LINK and submitted_file:
            errors["file"] = "Link resources cannot include an uploaded file."
        if (
            resource_type == Resource.ResourceType.LINK
            and resource is not None
            and "resource_type" in attrs
            and resource.file
        ):
            errors["resource_type"] = "A resource with an existing file cannot be changed to a link."
        if submitted_file and resource_type != Resource.ResourceType.LINK:
            try:
                validate_resource_file(submitted_file, resource_type)
            except ResourceFileValidationError as error:
                errors["file"] = str(error)
        if errors:
            raise serializers.ValidationError(errors)
        return attrs

    def _upload_to_cloudinary(self, validated_data: dict[str, object]) -> CloudinaryUploadResult | None:
        if not settings.CLOUDINARY_CONFIGURED or not validated_data.get("file"):
            return None

        uploader = validated_data.get("uploader") or (
            self.instance.uploader if isinstance(self.instance, Resource) else None
        )
        if uploader is None:
            raise serializers.ValidationError({"file": "A resource owner is required for file storage."})
        resource_type = validated_data.get(
            "resource_type",
            self.instance.resource_type if isinstance(self.instance, Resource) else None,
        )
        try:
            result = upload_resource_file(
                validated_file=validated_data["file"],
                resource_type=resource_type,
                uploader_id=uploader.pk,
            )
        except CloudinaryUploadError as error:
            raise serializers.ValidationError({"file": str(error)}) from error

        validated_data["file"] = result.reference
        return result

    def _client_upload_id(self):
        request = self.context.get("request")
        raw_upload_id = request.headers.get("X-Upload-ID") if request else None
        if not raw_upload_id:
            return None
        try:
            return UUID(raw_upload_id)
        except (TypeError, ValueError):
            return None

    def create(self, validated_data: dict[str, object]) -> Resource:
        client_upload_id = self._client_upload_id()
        uploader = validated_data.get("uploader")
        if client_upload_id and uploader:
            existing = Resource.objects.filter(client_upload_id=client_upload_id, uploader=uploader).first()
            if existing:
                return existing
            validated_data["client_upload_id"] = client_upload_id
        upload_result = self._upload_to_cloudinary(validated_data)
        try:
            with transaction.atomic():
                return super().create(validated_data)
        except Exception:
            discard_uploaded_resource(upload_result)
            raise

    def update(self, instance: Resource, validated_data: dict[str, object]) -> Resource:
        old_reference = instance.file.name if instance.file and is_cloudinary_reference(instance.file.name) else None
        upload_result = self._upload_to_cloudinary(validated_data)
        try:
            with transaction.atomic():
                updated_resource = super().update(instance, validated_data)
                if upload_result and old_reference and old_reference != upload_result.reference:
                    transaction.on_commit(
                        lambda: discard_cloudinary_reference(
                            old_reference,
                            excluding_resource_id=updated_resource.pk,
                        )
                    )
                return updated_resource
        except Exception:
            discard_uploaded_resource(upload_result)
            raise

    def to_representation(self, instance: Resource) -> dict[str, object]:
        representation = super().to_representation(instance)
        if instance.file and is_cloudinary_reference(instance.file.name):
            representation["file"] = cloudinary_reference_url(instance.file.name)
        return representation


class VideoSerializer(serializers.ModelSerializer):
    youtube_url = serializers.CharField(max_length=2048, write_only=True)
    youtube_video_id = serializers.CharField(read_only=True)
    original_url = serializers.URLField(read_only=True)
    uploader = PublicUserSerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    tag_ids = serializers.PrimaryKeyRelatedField(
        source="tags", many=True, queryset=Tag.objects.all(), write_only=True, required=False
    )

    class Meta:
        model = Video
        fields = (
            "id",
            "title",
            "slug",
            "description",
            "uploader",
            "youtube_url",
            "youtube_video_id",
            "original_url",
            "thumbnail_url",
            "subject",
            "topic",
            "course",
            "semester",
            "academic_level",
            "tags",
            "tag_ids",
            "duration_seconds",
            "status",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "slug", "uploader", "status", "created_at", "updated_at")

    def validate_youtube_url(self, value: str) -> str:
        try:
            return normalize_youtube_video_id(value, allow_raw_video_id=False)
        except ValidationError as error:
            raise serializers.ValidationError(error.messages) from error

    def validate(self, attrs: dict[str, object]) -> dict[str, object]:
        if "original_url" in self.initial_data:
            raise serializers.ValidationError({"original_url": "Use youtube_url for video submissions."})
        return attrs

    def create(self, validated_data: dict[str, object]) -> Video:
        validated_data["youtube_video_id"] = validated_data.pop("youtube_url")
        return super().create(validated_data)
