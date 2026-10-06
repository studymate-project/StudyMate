from django.test import Client, TestCase, override_settings
from django.urls import path
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView


class UnexpectedAPIErrorView(APIView):
    permission_classes = (AllowAny,)

    def get(self, request):
        raise RuntimeError(
            "SECRET_KEY=secret-value JWT=eyJhbGciOiJIUzI1NiJ9 "
            "DATABASE_URL=postgres://user:password@example.invalid/db "
            "password=plain-password C:\\private\\settings.py"
        )


urlpatterns = [path("api/test-unexpected-error/", UnexpectedAPIErrorView.as_view())]


class APIErrorHandlingTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.client.raise_request_exception = False

    @override_settings(DEBUG=False, ALLOWED_HOSTS=["testserver"], ROOT_URLCONF="backend.urls")
    def test_unknown_api_route_returns_json_without_debug_html(self):
        response = self.client.get("/api/route-does-not-exist/")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response["Content-Type"], "application/json")
        self.assertEqual(response.json(), {"detail": "Not found."})
        self.assertNotIn("Traceback", response.content.decode())

    @override_settings(DEBUG=False, ALLOWED_HOSTS=["testserver"], ROOT_URLCONF=__name__)
    def test_unexpected_api_error_is_generic_json_and_logs_redacted_diagnostics(self):
        with self.assertLogs("apps.core.exceptions", level="ERROR") as captured:
            response = self.client.get("/api/test-unexpected-error/")

        response_text = response.content.decode()
        log_text = "\n".join(captured.output)
        for sensitive_value in (
            "secret-value",
            "eyJhbGciOiJIUzI1NiJ9",
            "postgres://user:password@example.invalid/db",
            "plain-password",
        ):
            self.assertNotIn(sensitive_value, response_text)
            self.assertNotIn(sensitive_value, log_text)

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response["Content-Type"], "application/json")
        self.assertEqual(response.json(), {"detail": "Internal server error."})
        self.assertNotIn("Traceback", response_text)
        self.assertIn("Unhandled API exception", log_text)
        self.assertIn("RuntimeError", log_text)
        self.assertIn("SECRET_KEY=[redacted]", log_text)
        self.assertIn("DATABASE_URL=[redacted]", log_text)
        self.assertIn("password=[redacted]", log_text)
