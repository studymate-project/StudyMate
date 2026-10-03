from collections.abc import Iterable

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.core.model_utils import unique_slug

from .youtube import normalize_youtube_video_id


class PublicationStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    PENDING = "pending", "Pending review"
    PUBLISHED = "published", "Published"
    REJECTED = "rejected", "Rejected"
    ARCHIVED = "archived", "Archived"


class Tag(models.Model):
    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(max_length=90, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("name",)

    def __str__(self) -> str:
        return self.name


class Resource(models.Model):
    class ResourceType(models.TextChoices):
        FILE = "file", "File"
        VIDEO = "video", "Video"
        NOTES = "notes", "Notes"
        PDF = "pdf", "PDF"
        CHEAT_SHEET = "cheat_sheet", "Cheat sheet"
        PRESENTATION = "presentation", "Presentation"
        ASSIGNMENT = "assignment", "Assignment"
        QUESTION_PAPER = "question_paper", "Question paper"
        STUDY_GUIDE = "study_guide", "Study guide"
        LINK = "link", "Link"
        OTHER = "other", "Other"

    class Difficulty(models.TextChoices):
        BEGINNER = "beginner", "Beginner"
        INTERMEDIATE = "intermediate", "Intermediate"
        ADVANCED = "advanced", "Advanced"

    title = models.CharField(max_length=240)
    slug = models.SlugField(max_length=240, unique=True, blank=True)
    description = models.TextField(max_length=5000, blank=True)
    uploader = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="uploaded_resources")
    subject = models.CharField(max_length=120, db_index=True)
    topic = models.CharField(max_length=120, blank=True, db_index=True)
    course = models.CharField(max_length=160, blank=True, db_index=True)
    semester = models.CharField(max_length=80, blank=True, db_index=True)
    academic_level = models.ForeignKey(
        "education.AcademicLevel", on_delete=models.SET_NULL, null=True, blank=True, related_name="resources"
    )
    resource_type = models.CharField(max_length=20, choices=ResourceType.choices, db_index=True)
    file = models.FileField(upload_to="resources/", blank=True)
    external_url = models.URLField(blank=True)
    tags = models.ManyToManyField(Tag, blank=True, related_name="resources")
    difficulty = models.CharField(max_length=16, choices=Difficulty.choices, blank=True)
    status = models.CharField(max_length=12, choices=PublicationStatus.choices, default=PublicationStatus.DRAFT, db_index=True)
    client_upload_id = models.UUIDField(default=None, null=True, blank=True, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["uploader", "status", "created_at"]),
            models.Index(fields=["academic_level", "status", "created_at"]),
            models.Index(fields=["subject", "topic"]),
        ]

    def clean(self) -> None:
        if self.resource_type == self.ResourceType.LINK and not self.external_url:
            raise ValidationError({"external_url": "A link resource requires an external URL."})

    def save(
        self,
        *,
        force_insert: bool | tuple[type[models.Model], ...] = False,
        force_update: bool = False,
        using: str | None = None,
        update_fields: Iterable[str] | None = None,
    ) -> None:
        if not self.slug:
            self.slug = unique_slug(self, self.title)
        super().save(
            force_insert=force_insert,
            force_update=force_update,
            using=using,
            update_fields=update_fields,
        )

    def __str__(self) -> str:
        return self.title


class ResourceView(models.Model):
    resource = models.ForeignKey(Resource, on_delete=models.CASCADE, related_name="view_events")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="resource_view_events")
    viewed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["resource", "viewed_at"]), models.Index(fields=["user", "viewed_at"])]


class ResourceDownload(models.Model):
    resource = models.ForeignKey(Resource, on_delete=models.CASCADE, related_name="download_events")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="resource_download_events")
    downloaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["resource", "downloaded_at"]), models.Index(fields=["user", "downloaded_at"])]


class Video(models.Model):
    title = models.CharField(max_length=240)
    slug = models.SlugField(max_length=240, unique=True, blank=True)
    description = models.TextField(max_length=5000, blank=True)
    uploader = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="uploaded_videos")
    youtube_video_id = models.CharField(max_length=11, unique=True)
    original_url = models.URLField(blank=True)
    thumbnail_url = models.URLField(blank=True)
    subject = models.CharField(max_length=120, db_index=True)
    topic = models.CharField(max_length=120, blank=True, db_index=True)
    course = models.CharField(max_length=160, blank=True, db_index=True)
    semester = models.CharField(max_length=80, blank=True, db_index=True)
    academic_level = models.ForeignKey(
        "education.AcademicLevel", on_delete=models.SET_NULL, null=True, blank=True, related_name="videos"
    )
    tags = models.ManyToManyField(Tag, blank=True, related_name="videos")
    duration_seconds = models.PositiveIntegerField(null=True, blank=True)
    status = models.CharField(max_length=12, choices=PublicationStatus.choices, default=PublicationStatus.DRAFT, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["uploader", "status", "created_at"]),
            models.Index(fields=["academic_level", "status", "created_at"]),
            models.Index(fields=["subject", "topic"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(youtube_video_id__regex=r"^[A-Za-z0-9_-]{11}$"),
                name="resources_video_youtube_id_format",
            )
        ]

    def save(
        self,
        *,
        force_insert: bool | tuple[type[models.Model], ...] = False,
        force_update: bool = False,
        using: str | None = None,
        update_fields: Iterable[str] | None = None,
    ) -> None:
        self.youtube_video_id = normalize_youtube_video_id(self.youtube_video_id)
        if not self.slug:
            self.slug = unique_slug(self, self.title)
        super().save(
            force_insert=force_insert,
            force_update=force_update,
            using=using,
            update_fields=update_fields,
        )

    def __str__(self) -> str:
        return self.title
