import logging
from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import patch

from celery.exceptions import Retry
from django.test import SimpleTestCase, override_settings
from django.utils import timezone

from apps.users.retention import cleanup_expired_signup_verifications
from apps.users.tasks import (
    CLEANUP_RETRY_MAX_RETRIES,
    _cleanup_retry_delay,
    cleanup_expired_signup_verifications_task,
)


class FakeCleanupQuerySet:
    def __init__(self, manager, ids):
        self.manager = manager
        self.ids = list(ids)

    def select_for_update(self):
        return self

    def filter(self, **kwargs):
        if "pk__in" in kwargs:
            requested = set(kwargs["pk__in"])
            return FakeCleanupQuerySet(
                self.manager,
                [item for item in self.ids if item in requested],
            )
        return self

    def order_by(self, *args):
        return self

    def values_list(self, *args, **kwargs):
        return self

    def __getitem__(self, value):
        if isinstance(value, slice):
            return FakeCleanupQuerySet(self.manager, self.ids[value])
        return self.ids[value]

    def __iter__(self):
        return iter(self.ids)

    def delete(self):
        deleted = len(self.ids)
        self.manager.eligible_ids = [
            item for item in self.manager.eligible_ids if item not in self.ids
        ]
        return deleted, {"users.SignupEmailVerification": deleted}


class FakeCleanupManager:
    def __init__(self, eligible_ids):
        self.eligible_ids = list(eligible_ids)
        self.filters = []

    def select_for_update(self):
        return FakeCleanupQuerySet(self, self.eligible_ids)

    def filter(self, **kwargs):
        self.filters.append(kwargs)
        if "pk__in" in kwargs:
            requested = set(kwargs["pk__in"])
            ids = [item for item in self.eligible_ids if item in requested]
            return FakeCleanupQuerySet(self, ids)
        return FakeCleanupQuerySet(self, self.eligible_ids)


@override_settings(
    RETENTION_CLEANUP_ENABLED=True,
    SIGNUP_VERIFICATION_CLEANUP_RETENTION_SECONDS=60,
    RETENTION_CLEANUP_BATCH_SIZE=2,
    RETENTION_CLEANUP_MAX_BATCHES=10,
    RETENTION_CLEANUP_BATCH_PAUSE_SECONDS=0,
)
class RetentionCleanupTests(SimpleTestCase):
    def setUp(self):
        self.manager = FakeCleanupManager([1, 2, 3, 4, 5])
        self.model = patch(
            "apps.users.retention.SignupEmailVerification",
            SimpleNamespace(objects=self.manager),
        )
        self.model.start()
        self.addCleanup(self.model.stop)
        self.lock = patch(
            "apps.users.retention._cleanup_lock",
            return_value=nullcontext(True),
        )
        self.lock.start()
        self.addCleanup(self.lock.stop)
        self.atomic = patch(
            "apps.users.retention.transaction.atomic",
            return_value=nullcontext(),
        )
        self.atomic.start()
        self.addCleanup(self.atomic.stop)

    def test_deletes_in_bounded_batches_and_logs_measurable_counts(self):
        with self.assertLogs("apps.users.retention", level=logging.INFO) as captured:
            report = cleanup_expired_signup_verifications(
                now=timezone.now(),
                batch_size=2,
                max_batches=2,
            )

        self.assertEqual(report["processed_count"], 4)
        self.assertEqual(report["deleted_count"], 4)
        self.assertEqual(report["batches"], 2)
        self.assertTrue(report["limit_reached"])
        self.assertEqual(self.manager.eligible_ids, [5])
        output = "\n".join(captured.output)
        self.assertIn("processed_count=4", output)
        self.assertIn("deleted_count=4", output)
        self.assertIn("duration_seconds=", output)
        self.assertIn("last_success_at=", output)

    def test_repeated_run_is_idempotent_and_retains_noneligible_rows(self):
        first = cleanup_expired_signup_verifications(now=timezone.now())
        second = cleanup_expired_signup_verifications(now=timezone.now())

        self.assertEqual(first["deleted_count"], 5)
        self.assertEqual(second["deleted_count"], 0)
        self.assertFalse(first["limit_reached"])
        self.assertEqual(self.manager.eligible_ids, [])
        first_filter = self.manager.filters[0]
        self.assertEqual(first_filter["verified_at__isnull"], False)
        self.assertEqual(first_filter["otp_hash"], "")
        self.assertIn("expires_at__lt", first_filter)

    def test_overlapping_run_skips_without_deleting(self):
        self.lock.stop()
        self.lock = patch(
            "apps.users.retention._cleanup_lock",
            return_value=nullcontext(False),
        )
        self.lock.start()
        self.addCleanup(self.lock.stop)

        report = cleanup_expired_signup_verifications(now=timezone.now())

        self.assertEqual(report["status"], "skipped")
        self.assertEqual(report["reason"], "lock_not_acquired")
        self.assertEqual(report["deleted_count"], 0)
        self.assertEqual(self.manager.eligible_ids, [1, 2, 3, 4, 5])

    def test_database_failure_logs_safe_metrics_and_reraises(self):
        self.atomic.stop()
        with patch(
            "apps.users.retention.transaction.atomic",
            side_effect=RuntimeError("private database details"),
        ):
            with self.assertRaises(RuntimeError):
                with self.assertLogs("apps.users.retention", level=logging.ERROR) as captured:
                    cleanup_expired_signup_verifications(now=timezone.now())

        output = "\n".join(captured.output)
        self.assertIn("retention_cleanup_failed", output)
        self.assertIn("processed_count=0", output)
        self.assertIn("deleted_count=0", output)
        self.assertIn("failure_type=RuntimeError", output)
        self.assertNotIn("private database details", output)

    @patch(
        "apps.users.retention.SignupEmailVerification",
        SimpleNamespace(objects=FakeCleanupManager([])),
    )
    def test_disabled_cleanup_retains_records_and_does_not_delete(self):
        with self.settings(RETENTION_CLEANUP_ENABLED=False):
            report = cleanup_expired_signup_verifications()

        self.assertEqual(report["status"], "skipped")
        self.assertEqual(report["reason"], "disabled")
        self.assertEqual(report["deleted_count"], 0)

    @patch(
        "apps.users.retention.cleanup_expired_signup_verifications",
        side_effect=RuntimeError("database credentials should not be logged"),
    )
    def test_task_retries_failures_without_logging_exception_details(self, cleanup_mock):
        with patch.object(
            cleanup_expired_signup_verifications_task,
            "retry",
            side_effect=Retry(),
        ) as retry_mock:
            with self.assertRaises(Retry):
                with self.assertLogs("apps.users.tasks", level=logging.WARNING) as captured:
                    cleanup_expired_signup_verifications_task.run()

        cleanup_mock.assert_called_once_with()
        retry_mock.assert_called_once()
        self.assertEqual(retry_mock.call_args.kwargs["countdown"], 60)
        self.assertEqual(
            retry_mock.call_args.kwargs["max_retries"],
            CLEANUP_RETRY_MAX_RETRIES,
        )
        output = "\n".join(captured.output)
        self.assertIn("failure_type=RuntimeError", output)
        self.assertNotIn("database credentials", output)

    @patch(
        "apps.users.retention.cleanup_expired_signup_verifications",
        side_effect=RuntimeError("private database details"),
    )
    def test_retry_limit_logs_failure_without_another_retry(self, cleanup_mock):
        with patch.object(
            cleanup_expired_signup_verifications_task.request,
            "retries",
            CLEANUP_RETRY_MAX_RETRIES,
        ), patch.object(cleanup_expired_signup_verifications_task, "retry") as retry_mock:
            with self.assertRaises(RuntimeError):
                with self.assertLogs("apps.users.tasks", level=logging.ERROR) as captured:
                    cleanup_expired_signup_verifications_task.run()

        retry_mock.assert_not_called()
        self.assertIn("failure_type=RuntimeError", "\n".join(captured.output))
        self.assertNotIn("private database details", "\n".join(captured.output))

    def test_transient_retry_backoff_is_exponential_and_capped(self):
        self.assertEqual([_cleanup_retry_delay(number) for number in range(4)], [60, 120, 240, 300])
        self.assertEqual(_cleanup_retry_delay(10), 300)
