from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models


class Notification(models.Model):
    """A server-created event for a recipient.

    ``content_type`` and ``object_id`` intentionally support references to
    several existing domain models (for example, a resource, question, or
    answer) without separate nullable foreign keys for each event type.
    PostgreSQL cannot enforce the generic object's existence, so the future
    notification service must only assign allow-listed model types and an
    existing target after deriving the recipient from the domain event.
    """

    class NotificationType(models.TextChoices):
        RESOURCE_UPVOTED = "resource_upvoted", "Resource upvoted"
        QUESTION_ANSWERED = "question_answered", "Question answered"
        ANSWER_UPVOTED = "answer_upvoted", "Answer upvoted"
        NEW_FOLLOWER = "new_follower", "New follower"
        RESOURCE_SAVED = "resource_saved", "Resource saved"
        SYSTEM = "system", "System"

    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="notifications_created"
    )
    notification_type = models.CharField(max_length=24, choices=NotificationType.choices)
    content_type = models.ForeignKey(ContentType, on_delete=models.SET_NULL, null=True, blank=True)
    object_id = models.PositiveBigIntegerField(null=True, blank=True)
    content_object = GenericForeignKey("content_type", "object_id")
    message = models.CharField(max_length=500, blank=True)
    payload = models.JSONField(default=dict, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    notification_type__in=(
                        "resource_upvoted",
                        "question_answered",
                        "answer_upvoted",
                        "new_follower",
                        "resource_saved",
                        "system",
                    )
                ),
                name="notification_type_is_supported",
            ),
        ]
        indexes = [
            models.Index(fields=["recipient", "is_read", "created_at"]),
            models.Index(
                fields=["recipient", "-created_at", "-id"],
                name="notif_recipient_created_idx",
            ),
            models.Index(fields=["content_type", "object_id"]),
        ]

    def __str__(self):
        return f"{self.get_notification_type_display()} for {self.recipient}"
