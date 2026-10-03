"""Synchronous creation helpers for server-generated notifications."""

from collections.abc import Mapping
from typing import Any

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from apps.community.models import Answer, Question
from apps.resources.models import Resource

from .models import Notification


User = get_user_model()
ALLOWED_RELATED_OBJECT_TYPES = (User, Resource, Question, Answer)


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
