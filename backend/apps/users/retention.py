"""Opt-in, bounded cleanup for nonessential user-lifecycle bookkeeping."""

import logging
import threading
import time
from contextlib import contextmanager
from datetime import timedelta

from django.conf import settings
from django.db import connection, transaction
from django.utils import timezone

from .models import SignupEmailVerification


logger = logging.getLogger(__name__)

CLEANUP_NAME = "signup_verification_bookkeeping"
CLEANUP_LOCK_KEY = "studymate:retention:signup-verification"
_LOCAL_CLEANUP_LOCK = threading.Lock()


@contextmanager
def _cleanup_lock():
    """Serialize cleanup runs with PostgreSQL's deployment-safe DB lock.

    Production settings require PostgreSQL, so the advisory lock is the
    production mechanism.  The process-local fallback only keeps isolated
    non-PostgreSQL development/test runs from overlapping themselves; it is
    not presented as a distributed production lock.
    """

    is_postgresql = connection.vendor == "postgresql"
    acquired = False
    if is_postgresql:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT pg_try_advisory_lock(hashtext(%s))",
                [CLEANUP_LOCK_KEY],
            )
            acquired = bool(cursor.fetchone()[0])
    else:
        acquired = _LOCAL_CLEANUP_LOCK.acquire(blocking=False)

    if not acquired:
        yield False
        return

    try:
        yield True
    finally:
        if is_postgresql:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT pg_advisory_unlock(hashtext(%s))",
                    [CLEANUP_LOCK_KEY],
                )
        else:
            _LOCAL_CLEANUP_LOCK.release()


def cleanup_expired_signup_verifications(
    *,
    now=None,
    dry_run: bool = False,
    batch_size: int | None = None,
    max_batches: int | None = None,
    pause_seconds: int | None = None,
) -> dict[str, object]:
    """Delete only completed, expired verification bookkeeping rows.

    Pending verification rows are intentionally excluded because the resend
    flow uses them even after the OTP itself has expired.  A completed row is
    eligible only after its hash has been cleared and the explicit configured
    post-expiry retention window has elapsed.
    """

    started = time.monotonic()
    if not settings.RETENTION_CLEANUP_ENABLED:
        logger.info(
            "retention_cleanup_skipped cleanup_name=%s reason=disabled",
            CLEANUP_NAME,
        )
        return {
            "status": "skipped",
            "reason": "disabled",
            "cleanup_name": CLEANUP_NAME,
            "processed_count": 0,
            "deleted_count": 0,
            "batches": 0,
            "limit_reached": False,
            "duration_seconds": round(time.monotonic() - started, 3),
            "last_success_at": None,
            "dry_run": dry_run,
        }

    configured_retention = settings.SIGNUP_VERIFICATION_CLEANUP_RETENTION_SECONDS
    if configured_retention <= 0:
        logger.info(
            "retention_cleanup_skipped cleanup_name=%s reason=no_retention_window",
            CLEANUP_NAME,
        )
        return {
            "status": "skipped",
            "reason": "no_retention_window",
            "cleanup_name": CLEANUP_NAME,
            "processed_count": 0,
            "deleted_count": 0,
            "batches": 0,
            "limit_reached": False,
            "duration_seconds": round(time.monotonic() - started, 3),
            "last_success_at": None,
            "dry_run": dry_run,
        }

    batch_size = settings.RETENTION_CLEANUP_BATCH_SIZE if batch_size is None else batch_size
    max_batches = settings.RETENTION_CLEANUP_MAX_BATCHES if max_batches is None else max_batches
    pause_seconds = (
        settings.RETENTION_CLEANUP_BATCH_PAUSE_SECONDS
        if pause_seconds is None
        else pause_seconds
    )
    if not 1 <= batch_size <= 1000:
        raise ValueError("Cleanup batch size must be between 1 and 1000.")
    if not 1 <= max_batches <= 100:
        raise ValueError("Cleanup max batches must be between 1 and 100.")
    if pause_seconds < 0 or pause_seconds > 60:
        raise ValueError("Cleanup batch and pacing values must be bounded and non-negative.")
    if pause_seconds * max_batches >= settings.CELERY_TASK_SOFT_TIME_LIMIT:
        raise ValueError("Cleanup pacing must fit within the Celery soft time limit.")

    now = now or timezone.now()
    cutoff = now - timedelta(seconds=configured_retention)
    eligible_filters = {
        "verified_at__isnull": False,
        "otp_hash": "",
        "expires_at__lt": cutoff,
    }
    processed_count = 0
    deleted_count = 0
    batches = 0
    limit_reached = False

    try:
        with _cleanup_lock() as acquired:
            if not acquired:
                logger.info(
                    "retention_cleanup_skipped cleanup_name=%s reason=lock_not_acquired",
                    CLEANUP_NAME,
                )
                return {
                    "status": "skipped",
                    "reason": "lock_not_acquired",
                    "cleanup_name": CLEANUP_NAME,
                    "processed_count": 0,
                    "deleted_count": 0,
                    "batches": 0,
                    "limit_reached": False,
                    "duration_seconds": round(time.monotonic() - started, 3),
                    "last_success_at": None,
                    "dry_run": dry_run,
                }

            while batches < max_batches:
                with transaction.atomic():
                    ids = list(
                        SignupEmailVerification.objects.select_for_update()
                        .filter(**eligible_filters)
                        .order_by("pk")
                        .values_list("pk", flat=True)[:batch_size]
                    )
                    if not ids:
                        break

                    processed_count += len(ids)
                    batches += 1
                    if dry_run:
                        break

                    deleted, _ = SignupEmailVerification.objects.filter(
                        pk__in=ids,
                        **eligible_filters,
                    ).delete()
                    deleted_count += deleted
                    if deleted == 0:
                        break

                if batches < max_batches and pause_seconds:
                    time.sleep(pause_seconds)
            else:
                limit_reached = True
    except Exception as exc:
        logger.error(
            "retention_cleanup_failed cleanup_name=%s processed_count=%s "
            "deleted_count=%s batches=%s duration_seconds=%s failure_type=%s",
            CLEANUP_NAME,
            processed_count,
            deleted_count,
            batches,
            round(time.monotonic() - started, 3),
            type(exc).__name__,
        )
        raise

    duration_seconds = round(time.monotonic() - started, 3)
    last_success_at = timezone.now().isoformat()
    logger.info(
        "retention_cleanup_succeeded cleanup_name=%s processed_count=%s "
        "deleted_count=%s batches=%s duration_seconds=%s last_success_at=%s dry_run=%s",
        CLEANUP_NAME,
        processed_count,
        deleted_count,
        batches,
        duration_seconds,
        last_success_at,
        dry_run,
    )
    return {
        "status": "success",
        "cleanup_name": CLEANUP_NAME,
        "processed_count": processed_count,
        "deleted_count": deleted_count,
        "batches": batches,
        "limit_reached": limit_reached,
        "duration_seconds": duration_seconds,
        "last_success_at": last_success_at,
        "dry_run": dry_run,
    }
