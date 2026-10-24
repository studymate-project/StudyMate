from unittest.mock import patch

from django.test import RequestFactory, SimpleTestCase, override_settings

from apps.core.db_observability import SlowQueryLoggingMiddleware


class SlowQueryLoggingMiddlewareTests(SimpleTestCase):
    def setUp(self):
        self.request = RequestFactory().get("/api/resources/?token=do-not-log")
        self.request.resolver_match = type(
            "ResolverMatch",
            (),
            {"route": "api/resources/"},
        )()

    @override_settings(
        DB_SLOW_QUERY_LOGGING_ENABLED=True,
        DB_SLOW_QUERY_THRESHOLD_MS=100,
    )
    def test_slow_query_logs_metadata_without_sql_or_parameters(self):
        middleware = SlowQueryLoggingMiddleware(lambda request: None)
        with patch(
            "apps.core.db_observability.time.perf_counter",
            side_effect=(10.0, 10.4),
        ), self.assertLogs("apps.core.db_observability", level="WARNING") as captured:
            result = middleware._execute(
                lambda sql, params, many, context: "result",
                "SELECT password FROM users WHERE email = %s",
                ("private@example.test",),
                False,
                {"request": self.request},
            )

        self.assertEqual(result, "result")
        self.assertEqual(len(captured.records), 1)
        message = captured.output[0]
        self.assertIn("duration_ms=400.00", message)
        self.assertIn("operation=SELECT", message)
        self.assertNotIn("password", message)
        self.assertNotIn("private@example.test", message)
        self.assertNotIn("token=do-not-log", message)

    @override_settings(
        DB_SLOW_QUERY_LOGGING_ENABLED=True,
        DB_SLOW_QUERY_THRESHOLD_MS=100,
    )
    def test_fast_query_is_not_logged(self):
        middleware = SlowQueryLoggingMiddleware(lambda request: None)
        with patch(
            "apps.core.db_observability.time.perf_counter",
            side_effect=(10.0, 10.01),
        ), patch("apps.core.db_observability.logger.warning") as warning:
            middleware._execute(
                lambda sql, params, many, context: "result",
                "SELECT 1",
                (),
                False,
                {"request": self.request},
            )

        warning.assert_not_called()

    @override_settings(DB_SLOW_QUERY_LOGGING_ENABLED=False)
    def test_disabled_logging_does_not_install_execute_wrapper(self):
        middleware = SlowQueryLoggingMiddleware(lambda request: "response")
        with patch("apps.core.db_observability.connection.execute_wrapper") as wrapper:
            self.assertEqual(middleware(self.request), "response")

        wrapper.assert_not_called()
