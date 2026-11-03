from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.resources.models import Resource, Video
from apps.resources.services.cloudinary import CloudinaryUploadResult


@override_settings(
    SIGNUP_EMAIL_VERIFICATION_REQUIRED=False,
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "celery-independent-critical-path-tests",
        },
    },
    REST_FRAMEWORK={
        "DEFAULT_THROTTLE_CLASSES": [
            "rest_framework.throttling.AnonRateThrottle",
            "rest_framework.throttling.UserRateThrottle",
            "rest_framework.throttling.ScopedRateThrottle",
        ],
        "DEFAULT_THROTTLE_RATES": {
            "anon": "1000/hour",
            "user": "1000/hour",
            "auth_login": "1000/hour",
            "auth_signup": "1000/hour",
            "resource_write": "1000/hour",
        },
    },
)
class CeleryIndependentCriticalPathTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.signup_payload = {
            "name": "Worker Independent Student",
            "email": "worker-independent@example.com",
            "password": "A-strong-signup-password-42!",
            "college": "StudyMate University",
            "country": "India",
            "state": "Delhi",
            "city": "New Delhi",
        }

    def signup_and_login(self):
        with patch(
            "apps.users.tasks.send_signup_verification_email_task.delay",
            side_effect=AssertionError("signup must not enqueue email when verification is disabled"),
        ) as enqueue:
            signup = self.client.post("/api/auth/signup/", self.signup_payload, format="json")

        self.assertEqual(signup.status_code, 202)
        self.assertFalse(signup.data["verification_required"])
        enqueue.assert_not_called()
        user = get_user_model().objects.get(email=self.signup_payload["email"])
        self.assertTrue(user.is_active)

        login = self.client.post(
            "/api/auth/login/",
            {"email": self.signup_payload["email"], "password": self.signup_payload["password"]},
            format="json",
        )
        self.assertEqual(login.status_code, 200)
        self.assertIn("studymate_access", login.cookies)
        return user

    def test_signup_login_invalid_login_and_session_restore_without_worker(self):
        user = self.signup_and_login()

        invalid = self.client.post(
            "/api/auth/login/",
            {"email": self.signup_payload["email"], "password": "wrong-password"},
            format="json",
        )
        self.assertEqual(invalid.status_code, 401)

        current_user = self.client.get("/api/auth/me/")
        self.assertEqual(current_user.status_code, 200)
        self.assertEqual(current_user.data["user"]["id"], user.pk)

    def test_link_and_youtube_records_are_created_without_worker(self):
        self.signup_and_login()

        link = self.client.post(
            "/api/resources/",
            {
                "title": "Public link",
                "description": "External notes",
                "resource_type": "link",
                "external_url": "https://example.com/study-notes",
            },
            format="json",
        )
        self.assertEqual(link.status_code, 201)
        self.assertTrue(Resource.objects.filter(pk=link.data["id"], resource_type="link").exists())

        video = self.client.post(
            "/api/videos/",
            {
                "title": "Study video",
                "description": "A YouTube resource",
                "youtube_url": "https://youtu.be/dQw4w9WgXcQ",
            },
            format="json",
        )
        self.assertEqual(video.status_code, 201)
        self.assertTrue(Video.objects.filter(pk=video.data["id"], youtube_video_id="dQw4w9WgXcQ").exists())

    @override_settings(CLOUDINARY_CONFIGURED=True)
    @patch("apps.resources.serializers.cloudinary_reference_url", return_value="https://res.cloudinary.com/test/resource.pdf")
    @patch("apps.resources.serializers.upload_resource_file")
    def test_file_upload_calls_cloudinary_and_persists_record_without_worker(self, upload_resource_file, _cloudinary_url):
        self.signup_and_login()
        upload_resource_file.return_value = CloudinaryUploadResult(
            public_id="studymate/resources/pdf/uploader-1/resource.pdf",
            secure_url="https://res.cloudinary.com/test/resource.pdf",
            reference="cloudinary://studymate/resources/pdf/uploader-1/resource.pdf",
        )
        response = self.client.post(
            "/api/resources/",
            {
                "title": "Uploaded PDF",
                "description": "Cloudinary-backed notes",
                "resource_type": "pdf",
                "file": SimpleUploadedFile("resource.pdf", b"%PDF-1.7\ncontent", content_type="application/pdf"),
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 201)
        upload_resource_file.assert_called_once()
        self.assertTrue(Resource.objects.filter(pk=response.data["id"], file__startswith="cloudinary://").exists())
