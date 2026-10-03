"""Small API exception normalization built on DRF's default handler."""

import logging
from typing import Any

from django.conf import settings

from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


def api_exception_handler(exc: Exception, context: dict[str, Any]) -> Response | None:
    response = exception_handler(exc, context)
    if response is None:
        if settings.DEBUG:
            return None

        view = context.get("view")
        view_name = view.__class__.__name__ if view is not None else "unknown view"
        safe_exception = RuntimeError("Unhandled API exception")
        logger.error(
            "Unhandled API exception in %s (%s)",
            view_name,
            type(exc).__name__,
            exc_info=(RuntimeError, safe_exception, exc.__traceback__),
        )
        return Response({"detail": "Internal server error."}, status=500)

    detail = response.data.get("detail") if isinstance(response.data, dict) else None
    if response.status_code == 403 and getattr(detail, "code", None) == "not_authenticated":
        response.status_code = 401
    return response
