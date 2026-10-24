"""Small, opt-in metrics for the application's subject recommendation cache.

These counters intentionally cover only the cache namespace whose reads and
writes are controlled by StudyMate. Django/DRF throttling and other Redis
users are not inferred from them. Counter writes are best effort and never
change request behavior when the cache is unavailable.
"""

from datetime import datetime, timezone

from django.conf import settings
from django.core.cache import cache


CACHE_METRICS_NAMESPACE = "studymate:cache-metrics:v1:subjects"
CACHE_METRICS_TTL_SECONDS = 2 * 24 * 60 * 60
CACHE_METRIC_EVENTS = ("hit", "miss", "read_error", "write_error")


def _metric_key(event: str, *, now: datetime | None = None) -> str:
    if event not in CACHE_METRIC_EVENTS:
        raise ValueError(f"Unsupported cache metric event: {event}")
    current = now or datetime.now(timezone.utc)
    return f"{CACHE_METRICS_NAMESPACE}:{current:%Y%m%d}:{event}"


def record_cache_event(event: str) -> None:
    """Best-effort atomic counter increment for the current UTC day."""

    if not getattr(settings, "CACHE_METRICS_ENABLED", False):
        return

    key = _metric_key(event)
    try:
        # add() makes the first increment safe without a separate read. Redis
        # backends implement incr atomically; LocMemCache supports the same
        # interface for isolated tests and local development.
        cache.add(key, 0, timeout=CACHE_METRICS_TTL_SECONDS)
        cache.incr(key)
    except Exception:
        # Observability must not turn a cache outage into an application error.
        return


def read_current_metrics() -> dict[str, int]:
    """Return current-day counters without exposing cache keys or values."""

    if not getattr(settings, "CACHE_METRICS_ENABLED", False):
        return {}

    keys = {event: _metric_key(event) for event in CACHE_METRIC_EVENTS}
    try:
        values = cache.get_many(keys.values())
    except Exception:
        return {}
    return {
        event: int(values.get(key) or 0)
        for event, key in keys.items()
    }
