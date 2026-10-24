from datetime import timedelta
from unittest.mock import patch

from django.core import mail
from django.core.cache import cache
from django.contrib.auth import get_user_model
from django.test import TestCase, TransactionTestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from backend.celery import app as celery_app
from apps.users.models import SignupEmailVerification
from apps.users.services.email import send_signup_verification_email
from apps.users.services.verification import SignupEmailDeliveryError
from apps.users.tasks import send_signup_verification_email_task


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    DEFAULT_FROM_EMAIL="no-reply@example.com",
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "signup-verification-tests",
        },
    },
    SIGNUP_OTP_MAX_ATTEMPTS=3,
    REST_FRAMEWORK={
        "DEFAULT_THROTTLE_CLASSES": [
            "rest_framework.throttling.AnonRateThrottle",
            "rest_framework.throttling.UserRateThrottle",
            "rest_framework.throttling.ScopedRateThrottle",
        ],
        "DEFAULT_THROTTLE_RATES": {
            "anon": "1000/hour",
            "user": "1000/hour",
            "auth_signup": "100/hour",
            "auth_signup_verification_request": "100/hour",
            "auth_signup_verification_verify": "100/hour",
        },
    },
)
class SignupEmailVerificationTests(TestCase):
    def setUp(self):
        cache.clear()
        mail.get_connection()
        mail.outbox.clear()
        self.client = APIClient()
        self.payload = {
            "name": "Pending Student",
            "email": "pending.student@example.com",
            "password": "A-strong-signup-password-42!",
            "country": "India",
        }

    def signup(self):
        with patch("apps.users.tasks.send_signup_verification_email_task.delay") as enqueue:
            with self.captureOnCommitCallbacks(execute=True):
                response = self.client.post("/api/auth/signup/", self.payload, format="json")
        return response, enqueue

    @staticmethod
    def email_code_from_enqueue(enqueue):
        return enqueue.call_args.args[1]

    def test_signup_sends_hashed_otp_and_verification_activates_without_auth_cookies(self):
        response, enqueue = self.signup()

        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.data, {
            "detail": (
                "If an account is awaiting verification for this email, the verification "
                "request has been accepted."
            )
        })
        self.assertNotIn("otp", str(response.data).lower())
        enqueue.assert_called_once()

        user = get_user_model().objects.get(email=self.payload["email"])
        verification = SignupEmailVerification.objects.get(user=user)
        code = self.email_code_from_enqueue(enqueue)
        self.assertFalse(user.is_active)
        self.assertNotEqual(verification.otp_hash, code)
        self.assertNotIn(code, str(response.data))

        login_before_verification = self.client.post(
            "/api/auth/login/",
            {"email": self.payload["email"], "password": self.payload["password"]},
            format="json",
        )
        self.assertEqual(login_before_verification.status_code, 401)
        self.assertNotIn("studymate_access", login_before_verification.cookies)

        verify_response = self.client.post(
            "/api/auth/signup/verification/verify/",
            {"email": self.payload["email"], "code": code},
            format="json",
        )
        self.assertEqual(verify_response.status_code, 200)
        user.refresh_from_db()
        verification.refresh_from_db()
        self.assertTrue(user.is_active)
        self.assertTrue(verification.verified_at)
        self.assertEqual(verification.otp_hash, "")

        reused = self.client.post(
            "/api/auth/signup/verification/verify/",
            {"email": self.payload["email"], "code": code},
            format="json",
        )
        self.assertEqual(reused.status_code, 400)
        self.assertNotIn("studymate_access", verify_response.cookies)
        self.assertEqual(
            self.client.post(
                "/api/auth/login/",
                {"email": self.payload["email"], "password": self.payload["password"]},
                format="json",
            ).status_code,
            200,
        )

    def test_incorrect_codes_are_counted_and_blocked(self):
        _, enqueue = self.signup()
        email = self.payload["email"]
        for attempt in range(3):
            response = self.client.post(
                "/api/auth/signup/verification/verify/",
                {"email": email, "code": "000000"},
                format="json",
            )
            self.assertEqual(response.status_code, 400, attempt)

        verification = SignupEmailVerification.objects.get(email=email)
        self.assertEqual(verification.attempts, 3)
        correct = self.email_code_from_enqueue(enqueue)
        blocked = self.client.post(
            "/api/auth/signup/verification/verify/",
            {"email": email, "code": correct},
            format="json",
        )
        self.assertEqual(blocked.status_code, 400)
        self.assertFalse(get_user_model().objects.get(email=email).is_active)

    def test_expired_code_is_rejected(self):
        self.signup()
        email = self.payload["email"]
        SignupEmailVerification.objects.filter(email=email).update(
            expires_at=timezone.now() - timedelta(seconds=1)
        )

        response = self.client.post(
            "/api/auth/signup/verification/verify/",
            {"email": email, "code": "123456"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(get_user_model().objects.get(email=email).is_active)

    def test_resend_has_cooldown_and_rotates_code_after_cooldown(self):
        _, initial_enqueue = self.signup()
        email = self.payload["email"]
        first_code = self.email_code_from_enqueue(initial_enqueue)

        with patch("apps.users.tasks.send_signup_verification_email_task.delay") as enqueue:
            with self.captureOnCommitCallbacks(execute=True):
                cooldown_response = self.client.post(
                    "/api/auth/signup/verification/request/",
                    {"email": email},
                    format="json",
                )
        self.assertEqual(cooldown_response.status_code, 202)
        enqueue.assert_not_called()

        cache.clear()
        SignupEmailVerification.objects.filter(email=email).update(
            last_sent_at=timezone.now() - timedelta(minutes=2)
        )
        with patch("apps.users.tasks.send_signup_verification_email_task.delay") as enqueue:
            with self.captureOnCommitCallbacks(execute=True):
                resend_response = self.client.post(
                    "/api/auth/signup/verification/request/",
                    {"email": email},
                    format="json",
                )
        self.assertEqual(resend_response.status_code, 202)
        enqueue.assert_called_once()
        self.assertNotEqual(self.email_code_from_enqueue(enqueue), first_code)

    def test_duplicate_signup_does_not_create_or_send_another_account(self):
        self.signup()
        duplicate = {
            **self.payload,
            "name": "Different Name",
            "password": "weak",
            "email": self.payload["email"].upper(),
        }
        response = self.client.post("/api/auth/signup/", duplicate, format="json")

        self.assertEqual(response.status_code, 202)
        self.assertEqual(get_user_model().objects.filter(email__iexact=self.payload["email"]).count(), 1)
        self.assertEqual(SignupEmailVerification.objects.filter(email=self.payload["email"]).count(), 1)

    def test_already_registered_signup_is_generic_and_does_not_send(self):
        get_user_model().objects.create_user(
            username="registered-student",
            email=self.payload["email"],
            password="A-strong-existing-password-42!",
        )

        response = self.client.post("/api/auth/signup/", self.payload, format="json")

        self.assertEqual(response.status_code, 202)
        self.assertEqual(get_user_model().objects.filter(email=self.payload["email"]).count(), 1)
        self.assertFalse(SignupEmailVerification.objects.exists())

    @override_settings(SIGNUP_OTP_EMAIL_RATE_LIMIT=1)
    def test_email_send_rate_limit_is_separate_from_resend_cooldown(self):
        self.signup()
        email = self.payload["email"]
        SignupEmailVerification.objects.filter(email=email).update(
            last_sent_at=timezone.now() - timedelta(minutes=2)
        )

        with patch("apps.users.tasks.send_signup_verification_email_task.delay") as enqueue:
            with self.captureOnCommitCallbacks(execute=True):
                response = self.client.post(
                    "/api/auth/signup/verification/request/",
                    {"email": email},
                    format="json",
                )

        self.assertEqual(response.status_code, 202)
        enqueue.assert_not_called()

    def test_enqueue_failure_is_not_silently_converted_to_success(self):
        with patch(
            "apps.users.tasks.send_signup_verification_email_task.delay",
            side_effect=RuntimeError("broker unavailable"),
        ) as enqueue:
            with self.assertRaises(SignupEmailDeliveryError):
                with self.captureOnCommitCallbacks(execute=True):
                    self.client.post("/api/auth/signup/", self.payload, format="json")

        enqueue.assert_called_once()
        verification = SignupEmailVerification.objects.get(email=self.payload["email"])
        self.assertIsNone(verification.last_sent_at)

    def test_email_backend_failure_is_not_silenced(self):
        with patch(
            "apps.users.services.email.send_mail",
            side_effect=RuntimeError("SMTP unavailable"),
        ):
            with self.assertRaises(RuntimeError):
                send_signup_verification_email(
                    email="recipient@example.com",
                    otp="123456",
                )

    def test_celery_task_sends_email_without_returning_otp(self):
        result = send_signup_verification_email_task.run(
            "task-recipient@example.com",
            "123456",
        )

        self.assertIsNone(result)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["task-recipient@example.com"])
        self.assertIn("123456", mail.outbox[0].body)

    def test_duplicate_email_task_delivery_sends_once_for_current_verification(self):
        _, enqueue = self.signup()
        verification = SignupEmailVerification.objects.get(email=self.payload["email"])
        otp = self.email_code_from_enqueue(enqueue)

        send_signup_verification_email_task.run(
            self.payload["email"],
            otp,
            verification_id=verification.pk,
        )
        send_signup_verification_email_task.run(
            self.payload["email"],
            otp,
            verification_id=verification.pk,
        )

        verification.refresh_from_db()
        self.assertIsNotNone(verification.email_sent_at)
        self.assertEqual(len(mail.outbox), 1)

    def test_celery_dispatch_includes_verification_identifier(self):
        _, enqueue = self.signup()

        self.assertIsInstance(enqueue.call_args.kwargs["verification_id"], int)
        self.assertGreater(enqueue.call_args.kwargs["verification_id"], 0)

    def test_celery_worker_discovers_signup_email_task(self):
        self.assertIn(
            "apps.users.tasks.send_signup_verification_email_task",
            celery_app.tasks,
        )

    def test_request_for_unknown_email_is_generic(self):
        response = self.client.post(
            "/api/auth/signup/verification/request/",
            {"email": "unknown@example.com"},
            format="json",
        )

        self.assertEqual(response.status_code, 202)
        self.assertFalse(SignupEmailVerification.objects.exists())
        self.assertNotIn("unknown@example.com", str(response.data))


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    DEFAULT_FROM_EMAIL="no-reply@example.com",
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "signup-verification-failure-tests",
        },
    },
    REST_FRAMEWORK={
        "DEFAULT_THROTTLE_CLASSES": [
            "rest_framework.throttling.AnonRateThrottle",
            "rest_framework.throttling.UserRateThrottle",
            "rest_framework.throttling.ScopedRateThrottle",
        ],
        "DEFAULT_THROTTLE_RATES": {
            "anon": "1000/hour",
            "user": "1000/hour",
            "auth_signup": "100/hour",
            "auth_signup_verification_request": "100/hour",
            "auth_signup_verification_verify": "100/hour",
        },
    },
)
class SignupEmailDispatchFailureTests(TransactionTestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.payload = {
            "name": "Dispatch Failure Student",
            "email": "dispatch.failure@example.com",
            "password": "A-strong-signup-password-42!",
            "country": "India",
        }

    def test_signup_reports_enqueue_failure_instead_of_returning_202(self):
        with patch(
            "apps.users.tasks.send_signup_verification_email_task.delay",
            side_effect=RuntimeError("broker unavailable"),
        ):
            response = self.client.post("/api/auth/signup/", self.payload, format="json")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            response.data["detail"],
            "Verification email delivery is temporarily unavailable. Please try again.",
        )
        verification = SignupEmailVerification.objects.get(email=self.payload["email"])
        self.assertIsNone(verification.last_sent_at)

    def test_resend_reports_enqueue_failure_and_keeps_code_recoverable(self):
        with patch("apps.users.tasks.send_signup_verification_email_task.delay"):
            self.client.post("/api/auth/signup/", self.payload, format="json")

        verification = SignupEmailVerification.objects.get(email=self.payload["email"])
        verification.last_sent_at = timezone.now() - timedelta(minutes=2)
        verification.save(update_fields=("last_sent_at", "updated_at"))
        cache.clear()

        with patch(
            "apps.users.tasks.send_signup_verification_email_task.delay",
            side_effect=RuntimeError("broker unavailable"),
        ):
            response = self.client.post(
                "/api/auth/signup/verification/request/",
                {"email": self.payload["email"]},
                format="json",
            )

        self.assertEqual(response.status_code, 503)
        verification.refresh_from_db()
        self.assertIsNone(verification.last_sent_at)
