from unittest.mock import patch

from django.test import TestCase, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from .models import StudentProfile


class ProfileAvatarAPITests(TestCase):
    cloudinary_settings = {
        "CLOUDINARY_CONFIGURED": True,
        "CLOUDINARY_STORAGE": {
            "CLOUD_NAME": "test-cloud",
            "API_KEY": "test-key",
            "API_SECRET": "test-secret",
            "SECURE": True,
            "PREFIX": "",
        },
        "CLOUDINARY_RESOURCE_FOLDER": "studymate/resources",
        "CLOUDINARY_AVATAR_FOLDER": "studymate/avatars",
        "STORAGES": {
            "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
            "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
            "cloudinary_media": {"BACKEND": "cloudinary_storage.storage.RawMediaCloudinaryStorage"},
            "cloudinary_images": {"BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage"},
        },
    }

    def setUp(self):
        from django.contrib.auth import get_user_model

        user_model = get_user_model()
        self.owner = user_model.objects.create_user(username="avatar-owner", password="not-used-in-test")
        self.other_user = user_model.objects.create_user(username="avatar-other", password="not-used-in-test")
        self.profile = StudentProfile.objects.create(user=self.owner)
        self.client = APIClient()

    @staticmethod
    def png_upload(name="avatar.png", content=b"\x89PNG\r\n\x1a\nvalid-image"):
        return SimpleUploadedFile(name, content, content_type="image/png")

    @override_settings(**cloudinary_settings)
    @patch("cloudinary.uploader.upload")
    def test_owner_uploads_avatar_and_api_persists_public_url(self, upload_mock):
        upload_mock.return_value = {"public_id": "studymate/avatars/user-1/avatar.png"}
        self.client.force_authenticate(user=self.owner)

        response = self.client.patch(
            f"/api/users/{self.owner.username}/",
            {"avatar_file": self.png_upload()},
            format="multipart",
        )

        self.assertEqual(response.status_code, 200)
        self.profile.refresh_from_db()
        self.assertTrue(self.profile.avatar_url.startswith("https://"))
        self.assertEqual(
            self.profile.avatar_reference,
            "cloudinary://studymate/avatars/user-1/avatar.png",
        )
        self.assertEqual(response.data["avatar_url"], self.profile.avatar_url)
        self.assertNotIn("avatar_reference", response.data)
        upload_mock.assert_called_once()

        persisted_response = self.client.get(f"/api/users/{self.owner.username}/")
        self.assertEqual(persisted_response.data["avatar_url"], self.profile.avatar_url)

    def test_owner_can_store_https_avatar_url_and_rejects_unsafe_urls(self):
        self.client.force_authenticate(user=self.owner)

        valid_response = self.client.patch(
            f"/api/users/{self.owner.username}/",
            {"avatar_url": "https://images.example.test/profile.png"},
            format="json",
        )
        invalid_response = self.client.patch(
            f"/api/users/{self.owner.username}/",
            {"avatar_url": "http://images.example.test/profile.png"},
            format="json",
        )

        self.assertEqual(valid_response.status_code, 200)
        self.assertEqual(invalid_response.status_code, 400)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.avatar_url, "https://images.example.test/profile.png")
        self.assertEqual(self.profile.avatar_reference, "")

    @override_settings(**cloudinary_settings)
    @patch("cloudinary.uploader.destroy")
    @patch("cloudinary.uploader.upload")
    def test_replacing_uploaded_avatar_cleans_previous_cloudinary_asset(self, upload_mock, destroy_mock):
        self.profile.avatar_url = "https://res.cloudinary.com/test-cloud/raw/upload/old.png"
        self.profile.avatar_reference = "cloudinary://studymate/avatars/user-1/old.png"
        self.profile.save(update_fields=("avatar_url", "avatar_reference"))
        upload_mock.return_value = {"public_id": "studymate/avatars/user-1/new.png"}
        destroy_mock.return_value = {"result": "ok"}
        self.client.force_authenticate(user=self.owner)

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.patch(
                f"/api/users/{self.owner.username}/",
                {"avatar_file": self.png_upload("new.png")},
                format="multipart",
            )

        self.assertEqual(response.status_code, 200)
        self.profile.refresh_from_db()
        self.assertEqual(
            self.profile.avatar_reference,
            "cloudinary://studymate/avatars/user-1/new.png",
        )
        destroy_mock.assert_called_once_with(
            "studymate/avatars/user-1/old.png",
            invalidate=True,
            resource_type="image",
        )

    @override_settings(**cloudinary_settings)
    @patch("cloudinary.uploader.upload")
    def test_invalid_avatar_is_rejected_before_cloudinary_upload(self, upload_mock):
        self.client.force_authenticate(user=self.owner)

        response = self.client.patch(
            f"/api/users/{self.owner.username}/",
            {"avatar_file": SimpleUploadedFile("avatar.png", b"not-an-image", content_type="image/png")},
            format="multipart",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("avatar_file", response.data)
        upload_mock.assert_not_called()
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.avatar_url, "")

    @override_settings(**cloudinary_settings)
    @patch("cloudinary.uploader.upload")
    def test_only_owner_can_upload_or_update_avatar(self, upload_mock):
        self.client.force_authenticate(user=self.other_user)

        upload_response = self.client.patch(
            f"/api/users/{self.owner.username}/",
            {"avatar_file": self.png_upload()},
            format="multipart",
        )
        url_response = self.client.patch(
            f"/api/users/{self.owner.username}/",
            {"avatar_url": "https://images.example.test/other.png"},
            format="json",
        )

        self.assertEqual(upload_response.status_code, 403)
        self.assertEqual(url_response.status_code, 403)
        upload_mock.assert_not_called()
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.avatar_url, "")
