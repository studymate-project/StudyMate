"""Small API exception normalization built on DRF's default handler."""

import logging
import re
from typing import Any

from django.conf import settings

from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)

_SENSITIVE_EXCEPTION_VALUE = re.compile(
    r"(?i)\b(SECRET_KEY|JWT(?:_[A-Z_]+)?|DATABASE_URL|password|token)\s*=\s*[^\s,;]+"
)


def _safe_exception_message(exc: Exception) -> str:
    """Keep useful database diagnostics out of logs' secret-bearing values."""

    message = " ".join(str(exc).split())
    if not message:
        return "(no exception message)"
    redacted_message = _SENSITIVE_EXCEPTION_VALUE.sub(r"\1=[redacted]", message)
    return redacted_message[:500]


def api_exception_handler(exc: Exception, context: dict[str, Any]) -> Response | None:
    response = exception_handler(exc, context)
    if response is None:
        if settings.DEBUG:
            return None

        view = context.get("view")
        view_name = view.__class__.__name__ if view is not None else "unknown view"
        safe_message = _safe_exception_message(exc)
        safe_exception = RuntimeError(safe_message)
        logger.error(
            "Unhandled API exception in %s (%s): %s",
            view_name,
            type(exc).__name__,
            safe_message,
            exc_info=(type(exc), safe_exception, exc.__traceback__),
        )
        return Response({"detail": "Internal server error."}, status=500)

    detail = response.data.get("detail") if isinstance(response.data, dict) else None
    if response.status_code == 403 and getattr(detail, "code", None) == "not_authenticated":
        response.status_code = 401
    return response
