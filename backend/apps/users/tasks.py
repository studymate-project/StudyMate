"""Background jobs for user lifecycle email delivery."""

from celery import shared_task

from .services.email import send_signup_verification_email


@shared_task(
    bind=True,
    acks_late=True,
    ignore_result=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def send_signup_verification_email_task(self, email: str, otp: str) -> None:
    """Deliver one OTP email without returning or logging its contents."""

    send_signup_verification_email(email=email, otp=otp)
