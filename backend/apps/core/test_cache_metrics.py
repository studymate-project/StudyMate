import json
from io import StringIO
from unittest.mock import patch

from django.core.cache import cache
from django.core.management import call_command
from django.conf import settings
from django.test import SimpleTestCase, override_settings

from apps.core.cache_metrics import (
    CACHE_METRICS_TTL_SECONDS,
    read_current_metrics,
    record_cache_event,
)
from apps.resources import views as resource_views
from apps.resources.subject_cache import invalidate_subjects_cache


TEST_CACHE_SETTINGS = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "cache-metrics-tests",
    }
}


@override_settings(CACHES=TEST_CACHE_SETTINGS, CACHE_METRICS_ENABLED=True)
class CacheMetricsTests(SimpleTestCase):
    def setUp(self):
        cache.clear()

    def tearDown(self):
        cache.clear()

    def test_subject_cache_hit_and_miss_counters_are_namespace_scoped(self):
        key = "studymate:subjects:test-entry"

        self.assertIsNone(resource_views._subject_cache_get(key))
        cache.set(key, {"name": "safe-test-value"}, timeout=60)
        self.assertEqual(
            resource_views._subject_cache_get(key),
            {"name": "safe-test-value"},
        )

        metrics = read_current_metrics()
        self.assertEqual(metrics["miss"], 1)
        self.assertEqual(metrics["hit"], 1)
        self.assertEqual(metrics["read_error"], 0)
        self.assertEqual(metrics["write_error"], 0)

    def test_counter_write_uses_bounded_ttl(self):
        with patch(
            "apps.core.cache_metrics.cache.add",
            wraps=cache.add,
        ) as cache_add:
            record_cache_event("hit")

        self.assertEqual(
            cache_add.call_args.kwargs["timeout"],
            CACHE_METRICS_TTL_SECONDS,
        )

    def test_metrics_failure_never_breaks_cache_read(self):
        cache.set("subject-key", "value", timeout=60)
        with patch(
            "apps.core.cache_metrics.cache.add",
            side_effect=RuntimeError("metrics backend unavailable"),
        ):
            self.assertEqual(resource_views._subject_cache_get("subject-key"), "value")

    def test_version_key_uses_bounded_expiry(self):
        with patch("apps.resources.subject_cache.cache.set") as cache_set:
            invalidate_subjects_cache(user_id=42)

        self.assertEqual(
            cache_set.call_args.kwargs["timeout"],
            settings.SUBJECT_RECOMMENDATION_CACHE_VERSION_TTL_SECONDS,
        )


@override_settings(
    CACHES=TEST_CACHE_SETTINGS,
    CACHE_METRICS_ENABLED=False,
)
class CacheStatusCommandTests(SimpleTestCase):
    def test_locmem_status_does_not_attempt_redis_access(self):
        output = StringIO()
        with patch("django_redis.get_redis_connection") as get_connection:
            call_command("cache_status", "--json", stdout=output)

        get_connection.assert_not_called()
        report = json.loads(output.getvalue())
        self.assertIsNone(report["subject_cache_key_count"])
        self.assertFalse(report["cache_metrics_enabled"])

    @override_settings(
        CACHES={
            "default": {
                "BACKEND": "django_redis.cache.RedisCache",
                "LOCATION": "rediss://cache.example.test/0",
            }
        }
    )
    def test_redis_status_uses_a_capped_namespace_scan_without_printing_keys(self):
        class FakeRedis:
            def scan_iter(self, *, match, count):
                self.match = match
                self.count = count
                return iter([b"one", b"two", b"three"])

        fake_redis = FakeRedis()
        output = StringIO()
        with patch(
            "django_redis.get_redis_connection",
            return_value=fake_redis,
        ), patch(
            "django.core.cache.cache.make_key",
            return_value="safe-subject-pattern",
        ):
            call_command("cache_status", "--json", "--max-keys", "2", stdout=output)

        report = json.loads(output.getvalue())
        self.assertEqual(report["subject_cache_key_count"], 2)
        self.assertTrue(report["subject_cache_key_count_capped"])
        self.assertNotIn("one", output.getvalue())
