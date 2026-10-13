from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import F, Q


class SavedResource(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="saved_resources")
    resource = models.ForeignKey("resources.Resource", on_delete=models.CASCADE, related_name="saved_by")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "resource"], name="unique_saved_resource")]
        indexes = [models.Index(fields=["user", "created_at"]), models.Index(fields=["resource", "created_at"])]


class ResourceUpvote(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="resource_upvotes")
    resource = models.ForeignKey("resources.Resource", on_delete=models.CASCADE, related_name="upvotes")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "resource"], name="unique_resource_upvote")]
        indexes = [models.Index(fields=["user", "created_at"]), models.Index(fields=["resource", "created_at"])]


class ResourceRating(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="resource_ratings")
    resource = models.ForeignKey(
        "resources.Resource", on_delete=models.CASCADE, null=True, blank=True, related_name="ratings"
    )
    video = models.ForeignKey(
        "resources.Video", on_delete=models.CASCADE, null=True, blank=True, related_name="ratings"
    )
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(
                    (Q(resource__isnull=False) & Q(video__isnull=True))
                    | (Q(resource__isnull=True) & Q(video__isnull=False))
                ),
                name="resource_rating_one_target",
            ),
            models.CheckConstraint(
                condition=Q(rating__gte=1, rating__lte=5),
                name="resource_rating_value_range",
            ),
            models.UniqueConstraint(
                fields=["user", "resource"],
                condition=Q(resource__isnull=False),
                name="unique_user_resource_rating",
            ),
            models.UniqueConstraint(
                fields=["user", "video"],
                condition=Q(video__isnull=False),
                name="unique_user_video_rating",
            ),
        ]
        indexes = [
            models.Index(fields=["resource", "rating"]),
            models.Index(fields=["video", "rating"]),
            models.Index(fields=["user", "created_at"]),
        ]

    def __str__(self) -> str:
        target = self.resource or self.video
        return f"{self.user} rated {target} {self.rating}/5"


class QuestionUpvote(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="question_upvotes")
    question = models.ForeignKey("community.Question", on_delete=models.CASCADE, related_name="upvotes")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "question"], name="unique_question_upvote")]
        indexes = [models.Index(fields=["user", "created_at"]), models.Index(fields=["question", "created_at"])]


class AnswerUpvote(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="answer_upvotes")
    answer = models.ForeignKey("community.Answer", on_delete=models.CASCADE, related_name="upvotes")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "answer"], name="unique_answer_upvote")]
        indexes = [models.Index(fields=["user", "created_at"]), models.Index(fields=["answer", "created_at"])]


class UserFollow(models.Model):
    follower = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="following_relations")
    following = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="follower_relations")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["follower", "following"], name="unique_user_follow"),
            models.CheckConstraint(condition=~Q(follower=F("following")), name="prevent_self_follow"),
        ]
        indexes = [models.Index(fields=["follower", "created_at"]), models.Index(fields=["following", "created_at"])]

    def clean(self) -> None:
        if self.follower_id and self.follower_id == self.following_id:
            raise ValidationError({"following": "A user cannot follow themselves."})

    def __str__(self) -> str:
        return f"{self.follower} follows {self.following}"
