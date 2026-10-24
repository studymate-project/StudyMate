"""Bounded repair work for database-backed notifications."""

import logging

from celery import Task, shared_task


logger = logging.getLogger(__name__)

NOTIFICATION_RETRY_MAX_RETRIES = 3
NOTIFICATION_RETRY_BASE_DELAY_SECONDS = 30
NOTIFICATION_RETRY_MAX_DELAY_SECONDS = 300


def _retry_delay(retry_number: int) -> int:
    return min(
        NOTIFICATION_RETRY_BASE_DELAY_SECONDS * (2**retry_number),
        NOTIFICATION_RETRY_MAX_DELAY_SECONDS,
    )


def _create_question_answer_notification(answer_id: int):
    """Rebuild an answer notification from the persisted answer event."""

    from apps.community.models import Answer

    from .models import Notification
    from .services import create_notification

    answer = Answer.objects.select_related("question", "author").filter(pk=answer_id).first()
    if answer is None or answer.author_id == answer.question.author_id:
        return None

    return create_notification(
        recipient=answer.question.author,
        actor=answer.author,
        notification_type=Notification.NotificationType.QUESTION_ANSWERED,
        related_object=answer.question,
        payload={"answer_id": answer.pk},
    )


class NotificationRepairTask(Task):
    max_retries = NOTIFICATION_RETRY_MAX_RETRIES

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        logger.error(
            "Answer notification repair failed answer_id=%s failure_type=%s task_id=%s",
            kwargs.get("answer_id", args[0] if args else None),
            type(exc).__name__,
            task_id,
        )


@shared_task(
    bind=True,
    base=NotificationRepairTask,
    acks_late=True,
    ignore_result=True,
)
def ensure_question_answer_notification_task(self, answer_id: int) -> None:
    """Repair a missing answer notification with bounded retries.

    The service uses the persisted answer ID as the event identity. Repeated
    task execution therefore returns the existing notification instead of
    creating another record.
    """

    try:
        _create_question_answer_notification(answer_id)
    except Exception as exc:
        retry_number = getattr(self.request, "retries", 0)
        if retry_number >= self.max_retries:
            logger.error(
                "Answer notification repair retry limit reached answer_id=%s failure_type=%s",
                answer_id,
                type(exc).__name__,
            )
            raise

        logger.warning(
            "Answer notification repair failed answer_id=%s failure_type=%s retry_number=%s",
            answer_id,
            type(exc).__name__,
            retry_number + 1,
        )
        raise self.retry(
            exc=exc,
            countdown=_retry_delay(retry_number),
            max_retries=self.max_retries,
        )
