import logging
from unittest.mock import patch

from celery.exceptions import Retry
from django.test import SimpleTestCase

from apps.community.views import _queue_answer_notification_repair
from apps.notifications.tasks import (
    NOTIFICATION_RETRY_MAX_RETRIES,
    _retry_delay,
    ensure_question_answer_notification_task,
)


class NotificationTaskReliabilityTests(SimpleTestCase):
    @patch("apps.notifications.tasks._create_question_answer_notification")
    def test_successful_processing_and_repeated_execution_delegate_to_stable_event(self, create_mock):
        ensure_question_answer_notification_task.run(41)
        ensure_question_answer_notification_task.run(41)

        self.assertEqual(create_mock.call_count, 2)
        create_mock.assert_called_with(41)

    @patch(
        "apps.notifications.tasks._create_question_answer_notification",
        side_effect=RuntimeError("database temporarily unavailable"),
    )
    def test_transient_failure_requests_bounded_retry(self, create_mock):
        with patch.object(
            ensure_question_answer_notification_task,
            "retry",
            side_effect=Retry(),
        ) as retry_mock:
            with self.assertRaises(Retry):
                with self.assertLogs("apps.notifications.tasks", level=logging.WARNING) as captured:
                    ensure_question_answer_notification_task.run(41)

        retry_mock.assert_called_once()
        self.assertEqual(retry_mock.call_args.kwargs["countdown"], 30)
        self.assertEqual(
            retry_mock.call_args.kwargs["max_retries"],
            NOTIFICATION_RETRY_MAX_RETRIES,
        )
        output = "\n".join(captured.output)
        self.assertIn("answer_id=41", output)
        self.assertIn("failure_type=RuntimeError", output)
        self.assertNotIn("database temporarily unavailable", output)

    @patch(
        "apps.notifications.tasks._create_question_answer_notification",
        side_effect=RuntimeError("permanent database failure"),
    )
    def test_failure_at_retry_limit_is_raised_without_another_retry(self, create_mock):
        with patch.object(
            ensure_question_answer_notification_task.request,
            "retries",
            NOTIFICATION_RETRY_MAX_RETRIES,
        ), patch.object(ensure_question_answer_notification_task, "retry") as retry_mock:
            with self.assertRaises(RuntimeError):
                with self.assertLogs("apps.notifications.tasks", level=logging.ERROR) as captured:
                    ensure_question_answer_notification_task.run(41)

        retry_mock.assert_not_called()
        self.assertIn("failure_type=RuntimeError", "\n".join(captured.output))

    def test_transient_retry_backoff_is_exponential_and_capped(self):
        self.assertEqual([_retry_delay(number) for number in range(5)], [30, 60, 120, 240, 300])
        self.assertEqual(_retry_delay(10), 300)

    @patch("apps.notifications.tasks._create_question_answer_notification")
    @patch("apps.notifications.tasks.ensure_question_answer_notification_task.delay")
    def test_enqueue_failure_falls_back_to_synchronous_repair(self, delay_mock, create_mock):
        delay_mock.side_effect = RuntimeError("broker unavailable")

        with self.assertLogs("apps.community.views", level=logging.ERROR) as captured:
            _queue_answer_notification_repair(41)

        create_mock.assert_called_once_with(41)
        output = "\n".join(captured.output)
        self.assertIn("answer notification repair", output)
        self.assertNotIn("broker unavailable", output)

    @patch(
        "apps.notifications.tasks._create_question_answer_notification",
        side_effect=RuntimeError("sensitive internal details"),
    )
    @patch("apps.notifications.tasks.ensure_question_answer_notification_task.delay")
    def test_enqueue_and_synchronous_repair_fail_with_safe_logging(self, delay_mock, create_mock):
        delay_mock.side_effect = RuntimeError("broker credentials should not be logged")

        with self.assertLogs("apps.community.views", level=logging.ERROR) as captured:
            _queue_answer_notification_repair(41)

        messages = "\n".join(captured.output)
        self.assertIn("answer notification repair", messages)
        self.assertNotIn("broker credentials", messages)
        self.assertNotIn("sensitive internal details", messages)
