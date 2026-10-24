"""Synchronous creation helpers for server-generated notifications."""

from collections.abc import Mapping
from typing import Any

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import transaction

from apps.community.models import Answer, Question
from apps.resources.models import Resource, Video

from .models import Notification


User = get_user_model()
ALLOWED_RELATED_OBJECT_TYPES = (User, Resource, Video, Question, Answer)


def _validate_user(value: object, field_name: str) -> None:
    if not isinstance(value, User) or value.pk is None or value._state.adding:
        raise ValidationError({field_name: "A saved user instance is required."})


def _validate_related_object(value: object | None) -> None:
    if value is None:
        return
    if not isinstance(value, ALLOWED_RELATED_OBJECT_TYPES):
        raise ValidationError({"related_object": "The related object type is not supported."})
    if value.pk is None or value._state.adding:
        raise ValidationError({"related_object": "A saved related object is required."})
    if not value.__class__._default_manager.filter(pk=value.pk).exists():
        raise ValidationError({"related_object": "The related object does not exist."})


def create_notification(
    *,
    recipient: User,
    notification_type: str,
    actor: User | None = None,
    related_object: object | None = None,
    payload: Mapping[str, Any] | None = None,
) -> Notification:
    """Create one validated notification synchronously.

    This is an internal service API. Callers must derive ``recipient`` and
    ``actor`` from trusted domain objects; request payloads and user IDs are
    intentionally not accepted.
    """

    _validate_user(recipient, "recipient")
    if actor is not None:
        _validate_user(actor, "actor")

    supported_types = {choice for choice, _ in Notification.NotificationType.choices}
    if notification_type not in supported_types:
        raise ValidationError({"notification_type": "Unsupported notification type."})

    _validate_related_object(related_object)

    if payload is None:
        normalized_payload = {}
    elif not isinstance(payload, Mapping):
        raise ValidationError({"payload": "Payload must be a JSON object."})
    else:
        normalized_payload = dict(payload)

    # Answer notifications have a stable domain-event identifier already
    # present in the payload.  Serialize attempts for the answer row and
    # reuse an existing record so a repair task cannot create duplicates.
    answer_id = normalized_payload.get("answer_id")
    if (
        notification_type == Notification.NotificationType.QUESTION_ANSWERED
        and isinstance(related_object, Question)
        and isinstance(answer_id, int)
        and not isinstance(answer_id, bool)
        and answer_id > 0
        and actor is not None
    ):
        with transaction.atomic():
            answer = (
                Answer.objects.select_for_update()
                .filter(pk=answer_id, question_id=related_object.pk, author_id=actor.pk)
                .first()
            )
            if answer is not None:
                existing = (
                    Notification.objects.filter(
                        recipient_id=recipient.pk,
                        actor_id=actor.pk,
                        notification_type=notification_type,
                        content_type=ContentType.objects.get_for_model(related_object),
                        object_id=related_object.pk,
                        payload__answer_id=answer_id,
                    )
                    .order_by("pk")
                    .first()
                )
                if existing is not None:
                    return existing

            notification = Notification(
                recipient=recipient,
                actor=actor,
                notification_type=notification_type,
                content_object=related_object,
                payload=normalized_payload,
            )
            notification.full_clean()
            notification.save()
            return notification

    notification = Notification(
        recipient=recipient,
        actor=actor,
        notification_type=notification_type,
        content_object=related_object,
        payload=normalized_payload,
    )
    notification.full_clean()
    notification.save()
    return notification
