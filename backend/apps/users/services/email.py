"""Email delivery boundary for signup verification.

This function is deliberately small so it can be moved behind a Celery task
without changing the OTP generation or verification code.
"""

from django.conf import settings
from django.core.mail import send_mail


def send_signup_verification_email(*, email: str, otp: str) -> None:
    """Send one signup OTP through Django's configured email backend."""

    send_mail(
        subject="Verify your StudyMate email",
        message=(
            "Your StudyMate verification code is "
            f"{otp}. It expires in {settings.SIGNUP_OTP_TTL_SECONDS // 60} minutes."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[email],
        fail_silently=False,
    )
