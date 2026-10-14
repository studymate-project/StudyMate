from django.conf import settings
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVectorField
from django.db import models

from apps.core.model_utils import unique_slug
from apps.resources.models import PublicationStatus, Tag


class Question(models.Model):
    title = models.CharField(max_length=300)
    slug = models.SlugField(max_length=300, unique=True, blank=True)
    body = models.TextField(max_length=10000)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="questions")
    subject = models.CharField(max_length=120, db_index=True)
    topic = models.CharField(max_length=120, blank=True, db_index=True)
    academic_level = models.ForeignKey(
        "education.AcademicLevel", on_delete=models.SET_NULL, null=True, blank=True, related_name="questions"
    )
    tags = models.ManyToManyField(Tag, blank=True, related_name="questions")
    status = models.CharField(max_length=12, choices=PublicationStatus.choices, default=PublicationStatus.PUBLISHED, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    search_vector = SearchVectorField(null=True, editable=False)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["author", "created_at"]),
            models.Index(fields=["subject", "topic"]),
            models.Index(fields=["academic_level", "status", "created_at"]),
            GinIndex(fields=["search_vector"], name="community_question_search_fts"),
            GinIndex(
                fields=["title", "body", "subject", "topic"],
                name="community_question_search_trgm",
                opclasses=("gin_trgm_ops",) * 4,
            ),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slug(self, self.title)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


class Answer(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="answers")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="answers")
    body = models.TextField(max_length=10000)
    is_helpful = models.BooleanField(default=False)
    status = models.CharField(max_length=12, choices=PublicationStatus.choices, default=PublicationStatus.PUBLISHED, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("created_at",)
        indexes = [models.Index(fields=["question", "created_at"]), models.Index(fields=["author", "created_at"])]

    def __str__(self):
        return f"Answer by {self.author} on {self.question}"


class DiscussionComment(models.Model):
    resource = models.ForeignKey(
        "resources.Resource",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="discussion_comments",
    )
    video = models.ForeignKey(
        "resources.Video",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="discussion_comments",
    )
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="discussion_comments")
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="replies",
    )
    body = models.TextField(max_length=10000)
    status = models.CharField(
        max_length=12,
        choices=PublicationStatus.choices,
        default=PublicationStatus.PUBLISHED,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("created_at", "pk")
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(resource__isnull=False, video__isnull=True)
                    | models.Q(resource__isnull=True, video__isnull=False)
                ),
                name="community_discussion_one_target",
            ),
        ]
        indexes = [
            models.Index(
                fields=["resource", "parent", "created_at"],
                name="community_d_resourc_478f3f_idx",
            ),
            models.Index(
                fields=["video", "parent", "created_at"],
                name="community_d_video_i_e0b2f1_idx",
            ),
            models.Index(
                fields=["author", "created_at"],
                name="community_d_author__f70696_idx",
            ),
        ]

    def __str__(self):
        return f"Discussion comment by {self.author}"


class DiscussionCommentLike(models.Model):
    comment = models.ForeignKey(DiscussionComment, on_delete=models.CASCADE, related_name="likes")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="discussion_comment_likes")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["comment", "user"], name="community_discussion_like_unique"),
        ]
        indexes = [
            models.Index(fields=["user", "created_at"], name="community_d_user_id_b07716_idx"),
        ]
