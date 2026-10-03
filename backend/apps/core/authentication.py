"""JWT authentication that accepts access tokens from a secure cookie.

Authorization headers remain supported through SimpleJWT. Refresh tokens are
intentionally not read by this authenticator; they are reserved for a future
auth endpoint and are kept in a separate HTTP-only cookie.
"""

from django.conf import settings
from rest_framework.authentication import SessionAuthentication
from rest_framework_simplejwt.authentication import JWTAuthentication


class CookieJWTAuthentication(JWTAuthentication):
    """Authenticate with a Bearer header or the configured access-token cookie."""

    def authenticate(self, request):
        if self.get_header(request) is not None:
            return super().authenticate(request)

        raw_token = request.COOKIES.get(settings.JWT_ACCESS_COOKIE_NAME)
        if not raw_token:
            return None

        # Browser cookies are sent automatically, so unsafe cookie-authenticated
        # requests must pass Django/DRF's normal CSRF check. Header Bearer JWTs
        # remain usable for non-browser clients without this cookie requirement.
        SessionAuthentication().enforce_csrf(request)

        validated_token = self.get_validated_token(raw_token.encode('utf-8'))
        return self.get_user(validated_token), validated_token
