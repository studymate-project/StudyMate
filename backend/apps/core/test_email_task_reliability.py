import logging
import smtplib
from contextlib import nullcontext
from datetime import timedelta
from unittest.mock import patch

from celery.exceptions import Retry
from django.test import SimpleTestCase, override_settings
from django.utils import timezone

from apps.users.services.verification import (
    SignupEmailDeliveryError,
    _enqueue_email,
)
from apps.users.services.email import send_signup_verification_email
from apps.users.tasks import (
    EMAIL_RETRY_MAX_RETRIES,
    _retry_delay,
    PermanentEmailDeliveryError,
    TransientEmailDeliveryError,
    send_signup_verification_email_task,
)


class FakeVerification:
    email = "student@example.test"
    verified_at = None
    expires_at = timezone.now() + timedelta(minutes=10)
    otp_hash = "unused-by-mocked-current-state"
    email_sent_at = None

    def save(self, *, update_fields):
        self.saved_update_fields = update_fields


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    EMAIL_HOST="",
    EMAIL_HOST_USER="",
    EMAIL_HOST_PASSWORD="",
)
class SignupEmailTaskReliabilityTests(SimpleTestCase):
    def setUp(self):
        self.verification = FakeVerification()
        self.atomic = patch(
            "apps.users.tasks.transaction.atomic",
            return_value=nullcontext(),
        )
        self.atomic.start()
        self.addCleanup(self.atomic.stop)

    def run_current_task(self):
        with patch(
            "apps.users.tasks._load_verification_for_delivery",
            return_value=self.verification,
        ), patch(
            "apps.users.tasks._verification_is_current",
            return_value=True,
        ):
            return send_signup_verification_email_task.run(
                self.verification.email,
                "123456",
                verification_id=42,
            )

    def test_successful_delivery_marks_state(self):
        with patch(
            "apps.users.tasks.send_signup_verification_email"
        ) as send_email:
            result = self.run_current_task()

        self.assertIsNone(result)
        send_email.assert_called_once_with(
            email=self.verification.email,
            otp="123456",
        )
        self.assertIsNotNone(self.verification.email_sent_at)

    def test_transient_failure_requests_bounded_backoff_retry(self):
        retry = Retry()
        with patch(
            "apps.users.tasks.send_signup_verification_email",
            side_effect=ConnectionError("temporary mail service outage"),
        ), patch.object(
            send_signup_verification_email_task,
            "retry",
            return_value=retry,
        ) as retry_mock:
            with self.assertLogs("apps.users.tasks", level=logging.WARNING) as captured:
                with self.assertRaises(Retry):
                    self.run_current_task()

        retry_mock.assert_called_once()
        self.assertEqual(retry_mock.call_args.kwargs["countdown"], 60)
        self.assertEqual(
            retry_mock.call_args.kwargs["max_retries"],
            EMAIL_RETRY_MAX_RETRIES,
        )
        output = "\n".join(captured.output)
        self.assertIn("verification_id=42", output)
        self.assertNotIn("123456", output)
        self.assertNotIn(self.verification.email, output)

    def test_transient_failure_stops_after_retry_limit(self):
        with patch(
            "apps.users.tasks.send_signup_verification_email",
            side_effect=ConnectionError("temporary mail service outage"),
        ), patch.object(
            send_signup_verification_email_task.request,
            "retries",
            EMAIL_RETRY_MAX_RETRIES,
        ), patch.object(send_signup_verification_email_task, "retry") as retry_mock:
            with self.assertLogs("apps.users.tasks", level=logging.ERROR) as captured:
                with self.assertRaises(TransientEmailDeliveryError):
                    self.run_current_task()

        retry_mock.assert_not_called()
        output = "\n".join(captured.output)
        self.assertNotIn("123456", output)
        self.assertNotIn(self.verification.email, output)

    def test_transient_retry_backoff_is_exponential_and_capped(self):
        self.assertEqual([_retry_delay(number) for number in range(4)], [60, 120, 240, 300])
        self.assertEqual(_retry_delay(10), 300)

    def test_permanent_failure_is_not_retried(self):
        with patch(
            "apps.users.tasks.send_signup_verification_email",
            side_effect=smtplib.SMTPAuthenticationError(535, b"auth failed"),
        ), patch.object(send_signup_verification_email_task, "retry") as retry_mock:
            with self.assertRaises(PermanentEmailDeliveryError):
                with self.assertLogs("apps.users.tasks", level=logging.ERROR) as captured:
                    self.run_current_task()

        retry_mock.assert_not_called()
        output = "\n".join(captured.output)
        self.assertIn("failure_type=SMTPAuthenticationError", output)
        self.assertNotIn("auth failed", output)
        self.assertNotIn("123456", output)

    def test_permanent_smtp_response_failure_is_not_retried(self):
        with patch(
            "apps.users.tasks.send_signup_verification_email",
            side_effect=smtplib.SMTPResponseException(550, b"permanent failure"),
        ), patch.object(send_signup_verification_email_task, "retry") as retry_mock:
            with self.assertRaises(PermanentEmailDeliveryError):
                self.run_current_task()

        retry_mock.assert_not_called()

    def test_repeated_task_execution_skips_already_delivered_email(self):
        self.verification.email_sent_at = timezone.now()
        with patch(
            "apps.users.tasks.send_signup_verification_email"
        ) as send_email, self.assertLogs("apps.users.tasks", level=logging.INFO) as captured:
            self.run_current_task()

        send_email.assert_not_called()
        self.assertIn("duplicate", "\n".join(captured.output))

    def test_enqueue_failure_raises_without_logging_email_or_otp(self):
        with patch(
            "apps.users.tasks.send_signup_verification_email_task.delay",
            side_effect=RuntimeError("broker unavailable"),
        ), patch(
            "apps.users.services.verification.SignupEmailVerification.objects.filter"
        ) as filter_mock:
            with self.assertRaises(SignupEmailDeliveryError):
                with self.assertLogs(
                    "apps.users.services.verification", level=logging.ERROR
                ) as captured:
                    _enqueue_email(
                        verification_id=42,
                        email="student@example.test",
                        otp="123456",
                    )

        filter_mock.assert_not_called()
        output = "\n".join(captured.output)
        self.assertNotIn("student@example.test", output)
        self.assertNotIn("123456", output)
        self.assertIn("verification_id=42", output)

    def test_zero_message_backend_result_is_not_recorded_as_delivery(self):
        with patch(
            "apps.users.services.email.send_mail",
            return_value=0,
        ):
            with self.assertRaisesRegex(RuntimeError, "exactly one message"):
                send_signup_verification_email(
                    email="student@example.test",
                    otp="123456",
                )
