"""Secure signup email OTP lifecycle."""

import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone

from ..models import SignupEmailVerification


INVALID_CODE_MESSAGE = "Invalid or expired verification code."
EMAIL_DELIVERY_UNAVAILABLE_MESSAGE = "Verification email delivery is temporarily unavailable. Please try again."
GENERIC_REQUEST_MESSAGE = (
    "If an account is awaiting verification for this email, the verification "
    "request has been accepted."
)


class SignupEmailDeliveryError(RuntimeError):
    """Raised when the verification email cannot be handed to Celery."""


def generate_signup_otp() -> str:
    """Return a fixed-width numeric OTP using a cryptographically secure RNG."""

    upper_bound = 10 ** settings.SIGNUP_OTP_LENGTH
    return f"{secrets.randbelow(upper_bound):0{settings.SIGNUP_OTP_LENGTH}d}"


def _email_rate_key(email: str) -> str:
    return f"studymate:signup-otp:send:{email.casefold()}"


def _allow_email_delivery(email: str) -> bool:
    """Limit sends per normalized email in addition to endpoint throttles."""

    key = _email_rate_key(email)
    limit = settings.SIGNUP_OTP_EMAIL_RATE_LIMIT
    window = settings.SIGNUP_OTP_EMAIL_RATE_WINDOW_SECONDS
    if cache.add(key, 1, timeout=window):
        return True
    try:
        count = cache.incr(key)
    except ValueError:
        # A cache backend without atomic increment support should fail closed.
        return False
    if count <= limit:
        return True
    return False


def _enqueue_email(*, verification_id: int, email: str, otp: str) -> bool:
    """Enqueue delivery and mark the send time only after dispatch succeeds."""

    # Imported lazily to keep model/serializer imports independent of Celery
    # task discovery and to make dispatch easy to mock in tests.
    from ..tasks import send_signup_verification_email_task

    try:
        send_signup_verification_email_task.delay(email, otp)
    except Exception as exc:
        # Do not turn a broker failure into a successful-looking signup. The
        # OTP remains hashed and last_sent_at remains empty, so resend remains
        # a safe recovery path after the transient failure is resolved.
        raise SignupEmailDeliveryError from exc

    SignupEmailVerification.objects.filter(
        pk=verification_id,
        last_sent_at__isnull=True,
    ).update(last_sent_at=timezone.now())
    return True


def _schedule_email_enqueue(*, verification_id: int, email: str, otp: str) -> None:
    # The callback contains the OTP only in memory until it is handed to the
    # broker and never persists or logs it. A dispatch failure is allowed to
    # reach the API view so it cannot be reported as a successful signup.
    transaction.on_commit(
        lambda: _enqueue_email(
            verification_id=verification_id,
            email=email,
            otp=otp,
        ),
    )


def create_signup_verification(*, user) -> SignupEmailVerification:
    """Create hashed OTP state and schedule its first email delivery."""

    otp = generate_signup_otp()
    now = timezone.now()
    verification = SignupEmailVerification.objects.create(
        user=user,
        email=user.email,
        otp_hash=make_password(otp),
        expires_at=now + timedelta(seconds=settings.SIGNUP_OTP_TTL_SECONDS),
    )
    if _allow_email_delivery(user.email):
        _schedule_email_enqueue(
            verification_id=verification.pk,
            email=user.email,
            otp=otp,
        )
    return verification


def resend_signup_verification(*, email: str) -> bool:
    """Rotate and send an OTP when the pending account is eligible.

    The boolean is for internal tests and callers; API responses remain
    generic so cooldowns and account existence are not disclosed.
    """

    now = timezone.now()
    with transaction.atomic():
        verification = (
            SignupEmailVerification.objects.select_for_update()
            .select_related("user")
            .filter(email=email, verified_at__isnull=True, user__is_active=False)
            .first()
        )
        if verification is None:
            return False
        if verification.last_sent_at is not None and now < verification.last_sent_at + timedelta(
            seconds=settings.SIGNUP_OTP_RESEND_COOLDOWN_SECONDS
        ):
            return False
        if not _allow_email_delivery(email):
            return False

        otp = generate_signup_otp()
        verification.otp_hash = make_password(otp)
        verification.expires_at = now + timedelta(seconds=settings.SIGNUP_OTP_TTL_SECONDS)
        verification.attempts = 0
        verification.last_sent_at = None
        verification.save(
            update_fields=(
                "otp_hash",
                "expires_at",
                "attempts",
                "last_sent_at",
                "updated_at",
            )
        )
        _schedule_email_enqueue(
            verification_id=verification.pk,
            email=email,
            otp=otp,
        )
        return True


def verify_signup_otp(*, email: str, submitted_code: str) -> tuple[bool, str]:
    """Consume a valid OTP and activate its user exactly once."""

    with transaction.atomic():
        verification = (
            SignupEmailVerification.objects.select_for_update()
            .select_related("user")
            .filter(email=email)
            .first()
        )
        if (
            verification is None
            or verification.verified_at is not None
            or verification.user.is_active
            or verification.attempts >= settings.SIGNUP_OTP_MAX_ATTEMPTS
            or verification.expires_at <= timezone.now()
        ):
            return False, INVALID_CODE_MESSAGE

        if not submitted_code.isascii() or not submitted_code.isdigit() or len(submitted_code) != settings.SIGNUP_OTP_LENGTH:
            verification.attempts += 1
            verification.save(update_fields=("attempts", "updated_at"))
            return False, INVALID_CODE_MESSAGE

        if not check_password(submitted_code, verification.otp_hash):
            verification.attempts += 1
            verification.save(update_fields=("attempts", "updated_at"))
            return False, INVALID_CODE_MESSAGE

        user = verification.user
        user.is_active = True
        user.save(update_fields=("is_active",))
        verification.verified_at = timezone.now()
        # Removing the hash makes the code unusable even if a stale request is
        # replayed after the transaction commits.
        verification.otp_hash = ""
        verification.save(update_fields=("verified_at", "otp_hash", "updated_at"))
        return True, "Email verified. You can now log in."
