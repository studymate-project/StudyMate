"""Privacy-safe request-scoped database slow-query logging."""

import logging
import time

from django.conf import settings
from django.db import connection


logger = logging.getLogger(__name__)


def _operation(sql: str) -> str:
    """Return only the SQL verb; never include SQL text or parameters."""

    return (sql or "unknown").lstrip().split(None, 1)[0].upper()[:16]


class SlowQueryLoggingMiddleware:
    """Log only queries over the configured threshold, without SQL values."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not getattr(settings, "DB_SLOW_QUERY_LOGGING_ENABLED", False):
            return self.get_response(request)

        with connection.execute_wrapper(self._execute):
            return self.get_response(request)

    def _execute(self, execute, sql, params, many, context):
        started = time.perf_counter()
        try:
            return execute(sql, params, many, context)
        finally:
            elapsed_ms = (time.perf_counter() - started) * 1000
            if elapsed_ms >= settings.DB_SLOW_QUERY_THRESHOLD_MS:
                request = context.get("request") if isinstance(context, dict) else None
                resolver_match = getattr(request, "resolver_match", None)
                route = getattr(resolver_match, "route", None) or "unknown"
                method = getattr(request, "method", "unknown")
                logger.warning(
                    "slow_database_query duration_ms=%.2f db_alias=%s operation=%s method=%s route=%s",
                    elapsed_ms,
                    "default",
                    _operation(sql),
                    method,
                    route,
                )
