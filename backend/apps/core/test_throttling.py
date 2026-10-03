from contextlib import contextmanager
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import TestCase
from rest_framework.throttling import AnonRateThrottle, ScopedRateThrottle, UserRateThrottle
from rest_framework.test import APIClient


class APIThrottlingTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()

    @contextmanager
    def throttle_rates(self, **rates):
        configured = {
            **settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"],
            **rates,
        }
        with patch.object(AnonRateThrottle, "THROTTLE_RATES", configured), patch.object(
            UserRateThrottle, "THROTTLE_RATES", configured
        ), patch.object(ScopedRateThrottle, "THROTTLE_RATES", configured):
            yield

    def test_anonymous_and_authenticated_limits_are_separate(self):
        with self.throttle_rates(anon="2/minute", user="2/minute"):
            anonymous_responses = [self.client.get("/api/health/") for _ in range(3)]

        self.assertEqual([response.status_code for response in anonymous_responses], [200, 200, 429])

        user = User.objects.create_user(username="throttle-user", password="not-used-in-test")
        self.client.force_authenticate(user=user)
        with self.throttle_rates(anon="2/minute", user="2/minute"):
            authenticated_responses = [self.client.get("/api/auth/me/") for _ in range(3)]

        self.assertEqual([response.status_code for response in authenticated_responses], [200, 200, 429])

    def test_login_scope_throttles_excessive_attempts_with_safe_response(self):
        User.objects.create_user(
            username="login-throttle-user",
            email="login-throttle@example.com",
            password="A-strong-login-password-42!",
        )

        with self.throttle_rates(auth_login="1/minute"):
            first = self.client.post(
                "/api/auth/login/",
                {"email": "login-throttle@example.com", "password": "A-strong-login-password-42!"},
                format="json",
            )
            self.client.cookies.clear()
            second = self.client.post(
                "/api/auth/login/",
                {"email": "login-throttle@example.com", "password": "A-strong-login-password-42!"},
                format="json",
            )

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 429)
        self.assertIn("detail", second.data)
        self.assertNotIn("password", str(second.data).lower())
        self.assertNotIn("token", str(second.data).lower())

    def test_resource_creation_is_scoped_without_throttling_normal_reads(self):
        user = User.objects.create_user(username="resource-throttle-user", password="not-used-in-test")
        self.client.force_authenticate(user=user)
        payload = {
            "title": "Throttled notes",
            "subject": "Physics",
            "resource_type": "notes",
        }

        with self.throttle_rates(user="100/hour", resource_write="1/hour"):
            first = self.client.post("/api/resources/", payload, format="json")
            second = self.client.post("/api/resources/", payload, format="json")
            read = self.client.get("/api/resources/")

        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 429)
        self.assertEqual(read.status_code, 200)
