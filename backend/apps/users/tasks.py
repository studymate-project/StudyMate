"""Background jobs for user lifecycle email delivery."""

import logging
import smtplib

from celery import Task, shared_task
from django.contrib.auth.hashers import check_password
from django.core.mail import BadHeaderError
from django.db import transaction
from django.utils import timezone

from .services.email import send_signup_verification_email


logger = logging.getLogger(__name__)

EMAIL_RETRY_MAX_RETRIES = 3
EMAIL_RETRY_BASE_DELAY_SECONDS = 60
EMAIL_RETRY_MAX_DELAY_SECONDS = 300
CLEANUP_RETRY_MAX_RETRIES = 3
CLEANUP_RETRY_BASE_DELAY_SECONDS = 60
CLEANUP_RETRY_MAX_DELAY_SECONDS = 300


class PermanentEmailDeliveryError(RuntimeError):
    """An email failure that should not be retried by the worker."""


class TransientEmailDeliveryError(RuntimeError):
    """An email failure that may be retried within the bounded policy."""


def _is_permanent_email_failure(error: Exception) -> bool:
    if isinstance(
        error,
        (
            BadHeaderError,
            smtplib.SMTPAuthenticationError,
            smtplib.SMTPHeloError,
            smtplib.SMTPRecipientsRefused,
        ),
    ):
        return True
    if isinstance(error, smtplib.SMTPResponseException):
        return error.smtp_code >= 500
    return False


def _retry_delay(retry_number: int) -> int:
    return min(
        EMAIL_RETRY_BASE_DELAY_SECONDS * (2**retry_number),
        EMAIL_RETRY_MAX_DELAY_SECONDS,
    )


def _cleanup_retry_delay(retry_number: int) -> int:
    return min(
        CLEANUP_RETRY_BASE_DELAY_SECONDS * (2**retry_number),
        CLEANUP_RETRY_MAX_DELAY_SECONDS,
    )


def _load_verification_for_delivery(verification_id: int):
    from .models import SignupEmailVerification

    return (
        SignupEmailVerification.objects.select_for_update()
        .filter(pk=verification_id)
        .first()
    )


def _verification_is_current(verification, *, email: str, otp: str) -> bool:
    return bool(
        verification
        and verification.email == email
        and verification.verified_at is None
        and verification.expires_at > timezone.now()
        and check_password(otp, verification.otp_hash)
    )


class SignupEmailTask(Task):
    max_retries = EMAIL_RETRY_MAX_RETRIES

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        verification_id = kwargs.get("verification_id")
        logger.error(
            "Signup verification email task failed verification_id=%s failure_type=%s task_id=%s",
            verification_id,
            type(exc).__name__,
            task_id,
        )


@shared_task(
    bind=True,
    base=SignupEmailTask,
    acks_late=True,
    ignore_result=True,
)
def send_signup_verification_email_task(
    self,
    email: str,
    otp: str,
    verification_id: int | None = None,
) -> None:
    """Deliver the current OTP once, retrying only transient failures.

    ``verification_id`` is included for production dispatches. Calls without
    it remain useful for isolated callers/tests and intentionally skip the
    database idempotency guard.
    """

    def deliver() -> None:
        if verification_id is None:
            send_signup_verification_email(email=email, otp=otp)
            return

        with transaction.atomic():
            verification = _load_verification_for_delivery(verification_id)
            if not _verification_is_current(verification, email=email, otp=otp):
                logger.info(
                    "Skipping stale signup verification email task verification_id=%s",
                    verification_id,
                )
                return
            if verification.email_sent_at is not None:
                logger.info(
                    "Skipping duplicate signup verification email task verification_id=%s",
                    verification_id,
                )
                return

            send_signup_verification_email(email=email, otp=otp)
            verification.email_sent_at = timezone.now()
            verification.save(update_fields=("email_sent_at", "updated_at"))

    try:
        deliver()
    except Exception as exc:
        if _is_permanent_email_failure(exc):
            logger.error(
                "Permanent signup verification email failure verification_id=%s failure_type=%s",
                verification_id,
                type(exc).__name__,
            )
            raise PermanentEmailDeliveryError from None

        retry_number = getattr(self.request, "retries", 0)
        if retry_number >= self.max_retries:
            logger.error(
                "Signup verification email retry limit reached verification_id=%s failure_type=%s",
                verification_id,
                type(exc).__name__,
            )
            raise TransientEmailDeliveryError from None

        logger.warning(
            "Transient signup verification email failure verification_id=%s failure_type=%s retry_number=%s",
            verification_id,
            type(exc).__name__,
            retry_number + 1,
        )
        raise self.retry(
            exc=TransientEmailDeliveryError(),
            countdown=_retry_delay(retry_number),
            max_retries=self.max_retries,
        )


class RetentionCleanupTask(Task):
    max_retries = CLEANUP_RETRY_MAX_RETRIES

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        logger.error(
            "Retention cleanup task failed cleanup_name=signup_verification_bookkeeping "
            "failure_type=%s task_id=%s",
            type(exc).__name__,
            task_id,
        )


@shared_task(
    bind=True,
    base=RetentionCleanupTask,
    acks_late=True,
    ignore_result=True,
)
def cleanup_expired_signup_verifications_task(self) -> dict[str, object]:
    """Run the opt-in cleanup without enabling Celery Beat."""

    from .retention import cleanup_expired_signup_verifications

    try:
        return cleanup_expired_signup_verifications()
    except Exception as exc:
        retry_number = getattr(self.request, "retries", 0)
        if retry_number >= self.max_retries:
            logger.error(
                "Retention cleanup retry limit reached cleanup_name=signup_verification_bookkeeping "
                "failure_type=%s",
                type(exc).__name__,
            )
            raise

        logger.warning(
            "Retention cleanup failed cleanup_name=signup_verification_bookkeeping "
            "failure_type=%s retry_number=%s",
            type(exc).__name__,
            retry_number + 1,
        )
        raise self.retry(
            exc=exc,
            countdown=_cleanup_retry_delay(retry_number),
            max_retries=self.max_retries,
        )
