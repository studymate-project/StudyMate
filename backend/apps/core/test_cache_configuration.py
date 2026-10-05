from uuid import uuid4
from unittest import skipUnless

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.cache import cache
from django.test import SimpleTestCase
from django.contrib.auth.models import AnonymousUser
from rest_framework.throttling import AnonRateThrottle
from rest_framework.test import APIRequestFactory

from backend.settings import _build_cache_config


LIVE_REDIS_CONFIGURED = bool(
    settings.REDIS_URL
    and settings.CACHES["default"]["BACKEND"] == "django_redis.cache.RedisCache"
)


class CacheConfigurationTests(SimpleTestCase):
    def test_configured_redis_url_selects_django_redis_backend(self):
        redis_location = "configured-redis-location"

        cache_config = _build_cache_config(redis_location, debug=True)

        self.assertEqual(
            cache_config["default"]["BACKEND"],
            "django_redis.cache.RedisCache",
        )
        self.assertEqual(cache_config["default"]["LOCATION"], redis_location)

    def test_missing_redis_url_is_allowed_only_in_debug(self):
        local_config = _build_cache_config("", debug=True)

        self.assertEqual(
            local_config["default"]["BACKEND"],
            "django.core.cache.backends.locmem.LocMemCache",
        )
        with self.assertRaises(ImproperlyConfigured):
            _build_cache_config("", debug=False)

    def test_production_redis_requires_tls(self):
        with self.assertRaisesRegex(
            ImproperlyConfigured,
            "Production REDIS_URL must use the rediss:// TLS scheme",
        ):
            _build_cache_config("redis://cache.example.test:6379/0", debug=False)

        secure_config = _build_cache_config(
            "rediss://cache.example.test:6379/0",
            debug=False,
        )
        self.assertEqual(
            secure_config["default"]["BACKEND"],
            "django_redis.cache.RedisCache",
        )

    @skipUnless(
        LIVE_REDIS_CONFIGURED,
        "REDIS_URL is not configured; skipping live Redis integration test.",
    )
    def test_live_redis_cache_and_drf_throttle_counter(self):
        from django_redis import get_redis_connection
        from django_redis.cache import RedisCache
        from unittest.mock import patch

        cache_key = f"studymate:redis-verification:{uuid4().hex}"
        throttle_key = None
        secondary_cache = None
        factory = APIRequestFactory()
        request = factory.get(
            "/api/health/",
            REMOTE_ADDR=f"redis-verification-{uuid4().hex}",
        )
        request.user = AnonymousUser()

        try:
            self.assertTrue(cache.set(cache_key, "redis-round-trip", timeout=30))
            self.assertEqual(cache.get(cache_key), "redis-round-trip")

            redis_connection = get_redis_connection("default")
            self.assertTrue(redis_connection.exists(cache.make_key(cache_key)))

            with patch.object(AnonRateThrottle, "THROTTLE_RATES", {"anon": "2/minute"}):
                throttle = AnonRateThrottle()
                self.assertTrue(throttle.allow_request(request, object()))
                throttle_key = throttle.key
                self.assertIsNotNone(throttle_key)
                self.assertEqual(len(cache.get(throttle_key)), 1)

                secondary_cache = RedisCache(
                    settings.CACHES["default"]["LOCATION"],
                    settings.CACHES["default"],
                )
                self.assertEqual(
                    secondary_cache.get(throttle_key),
                    cache.get(throttle_key),
                )
                self.assertTrue(
                    redis_connection.exists(cache.make_key(throttle_key))
                )
        finally:
            cache.delete(cache_key)
            if throttle_key is not None:
                cache.delete(throttle_key)
            if secondary_cache is not None:
                secondary_cache.close()
