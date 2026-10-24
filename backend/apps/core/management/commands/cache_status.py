"""Report bounded, namespace-scoped cache metrics without exposing secrets."""

import json

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.core.cache_metrics import read_current_metrics


SUBJECT_CACHE_NAMESPACE = "studymate:subjects"
DEFAULT_SCAN_LIMIT = 10000


def _subject_key_count(max_keys: int) -> tuple[int | None, bool]:
    backend = settings.CACHES["default"].get("BACKEND", "")
    if backend != "django_redis.cache.RedisCache":
        return None, False

    try:
        from django.core.cache import cache
        from django_redis import get_redis_connection

        connection = get_redis_connection("default")
        pattern = cache.make_key(f"{SUBJECT_CACHE_NAMESPACE}:*")
        count = 0
        for _ in connection.scan_iter(match=pattern, count=1000):
            count += 1
            if count > max_keys:
                return max_keys, True
        return count, False
    except Exception:
        # Provider access and cache failures are operational status, not a
        # reason for this diagnostic command to print connection details.
        return None, False


class Command(BaseCommand):
    help = "Report bounded subject-cache metrics and key count."

    def add_arguments(self, parser):
        parser.add_argument(
            "--max-keys",
            type=int,
            default=DEFAULT_SCAN_LIMIT,
            help="Maximum subject-cache keys to scan before reporting a capped count.",
        )
        parser.add_argument("--json", action="store_true", dest="as_json")

    def handle(self, *args, **options):
        max_keys = options["max_keys"]
        if max_keys <= 0:
            self.stderr.write("--max-keys must be positive")
            return

        key_count, key_count_capped = _subject_key_count(max_keys)
        report = {
            "cache_backend": settings.CACHES["default"].get("BACKEND"),
            "cache_metrics_enabled": bool(
                getattr(settings, "CACHE_METRICS_ENABLED", False)
            ),
            "subject_cache_key_count": key_count,
            "subject_cache_key_count_capped": key_count_capped,
            "subject_cache_metrics_utc_day": read_current_metrics(),
        }

        if options["as_json"]:
            self.stdout.write(json.dumps(report, sort_keys=True))
            return

        for key, value in report.items():
            self.stdout.write(f"{key}={value}")
