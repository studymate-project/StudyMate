import os
import unittest
from unittest.mock import patch

from api_load_test import SafetyError, validate_runtime_configuration, validate_target


class TargetSafetyTests(unittest.TestCase):
    def test_local_requires_loopback(self):
        target = validate_target("http://127.0.0.1:8000", "local", None)
        self.assertEqual(target.hostname, "127.0.0.1")
        with self.assertRaises(SafetyError):
            validate_target("https://api.example.test", "local", None)

    def test_staging_requires_exact_marked_hostname(self):
        target = validate_target(
            "https://api-staging.example.test",
            "staging",
            "api-staging.example.test",
        )
        self.assertEqual(target.environment, "staging")
        with self.assertRaises(SafetyError):
            validate_target("https://api.example.test", "staging", "api.example.test")

    def test_production_marked_hosts_are_rejected(self):
        with self.assertRaises(SafetyError):
            validate_target("https://api-production.example.test", "staging", "api-production.example.test")
        with self.assertRaises(SafetyError):
            validate_target("https://studymate.onrender.com", "staging", "studymate.onrender.com")

    def test_explicitly_marked_render_staging_host_is_allowed(self):
        target = validate_target(
            "https://studymate-staging.onrender.com",
            "staging",
            "studymate-staging.onrender.com",
        )
        self.assertEqual(target.hostname, "studymate-staging.onrender.com")

    def test_urls_with_credentials_or_paths_are_rejected(self):
        with self.assertRaises(SafetyError):
            validate_target("http://user:password@127.0.0.1:8000", "local", None)
        with self.assertRaises(SafetyError):
            validate_target("http://127.0.0.1:8000/api", "local", None)


class RuntimeConfigurationSafetyTests(unittest.TestCase):
    def test_local_remote_database_is_rejected(self):
        with self.assertRaises(SafetyError):
            validate_runtime_configuration(
                "local",
                {"DATABASE_URL": "postgresql://user:pass@db.example.test/studymate"},
            )

    def test_known_production_cache_is_rejected(self):
        with self.assertRaises(SafetyError):
            validate_runtime_configuration(
                "staging",
                {"REDIS_URL": "rediss://default:secret@cache.upstash.io:6379/0"},
            )

    def test_isolated_loopback_configuration_is_allowed(self):
        validate_runtime_configuration(
            "local",
            {
                "DATABASE_URL": "postgresql://user:pass@127.0.0.1:5432/studymate",
                "REDIS_URL": "redis://127.0.0.1:6379/0",
                "CELERY_BROKER_URL": "redis://localhost:6379/1",
            },
        )

    @patch.dict(os.environ, {}, clear=True)
    def test_missing_runtime_services_do_not_bypass_target_validation(self):
        validate_runtime_configuration("local")


if __name__ == "__main__":
    unittest.main()
