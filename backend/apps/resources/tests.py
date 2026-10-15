from unittest.mock import patch
from uuid import uuid4

from django.conf import settings
from django.contrib.auth.models import User
from django.core.files.storage import FileSystemStorage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase, override_settings
from rest_framework import serializers
from rest_framework.test import APIClient

from backend.settings import _build_storage_config

from .models import PublicationStatus, Resource, Video
from .serializers import ResourceSerializer
from .services.cloudinary import _storage_name


class CloudinaryConfigurationTests(SimpleTestCase):
    def test_cloudinary_configuration_is_optional_and_consistent(self):
        configured = all(
            (
                settings.CLOUDINARY_CLOUD_NAME,
                settings.CLOUDINARY_API_KEY,
                settings.CLOUDINARY_API_SECRET,
            )
        )

        self.assertEqual(settings.CLOUDINARY_CONFIGURED, configured)
        if configured:
            self.assertIn("cloudinary_media", settings.STORAGES)
        else:
            self.assertNotIn("cloudinary_media", settings.STORAGES)

    def test_local_storage_config_uses_filesystem_storage(self):
        storage_config = _build_storage_config(debug=True, cloudinary_configured=False)

        self.assertEqual(
            storage_config["default"]["BACKEND"],
            "django.core.files.storage.FileSystemStorage",
        )

    def test_production_storage_config_uses_cloudinary_raw_storage(self):
        storage_config = _build_storage_config(debug=False, cloudinary_configured=True)

        self.assertEqual(
            storage_config["default"]["BACKEND"],
            "cloudinary_storage.storage.RawMediaCloudinaryStorage",
        )

    @override_settings(
        DEBUG=False,
        CLOUDINARY_CONFIGURED=True,
        STORAGES={
            "default": {
                "BACKEND": "cloudinary_storage.storage.RawMediaCloudinaryStorage",
            },
            "staticfiles": {
                "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
            },
        }
    )
    def test_production_resource_file_does_not_use_local_storage(self):
        file_field = Resource._meta.get_field("file")

        self.assertNotIsInstance(file_field.storage, FileSystemStorage)
        self.assertEqual(file_field.upload_to, "resources/")


class ResourceFileValidationTests(TestCase):
    @staticmethod
    def pdf_file(name: str = "resource.pdf", content: bytes = b"%PDF-1.7\nvalid") -> SimpleUploadedFile:
        return SimpleUploadedFile(name, content, content_type="application/pdf")

    @staticmethod
    def serializer_data(resource_type: str, file=None) -> dict[str, object]:
        data = {"title": "Uploaded resource", "subject": "Physics", "resource_type": resource_type}
        if file is not None:
            data["file"] = file
        return data

    def test_accepts_supported_pdf_for_pdf_resource(self):
        serializer = ResourceSerializer(
            data=self.serializer_data(Resource.ResourceType.PDF, self.pdf_file())
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_rejects_unsupported_extension_and_content(self):
        serializer = ResourceSerializer(
            data=self.serializer_data(
                Resource.ResourceType.NOTES,
                SimpleUploadedFile("script.exe", b"MZnot-a-document", content_type="application/octet-stream"),
            )
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("file", serializer.errors)

    def test_rejects_pdf_extension_when_content_is_not_pdf(self):
        serializer = ResourceSerializer(
            data=self.serializer_data(
                Resource.ResourceType.PDF,
                self.pdf_file(content=b"not-a-pdf"),
            )
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("content does not match", str(serializer.errors["file"][0]))

    def test_rejects_mismatched_declared_mime_type_with_valid_signature(self):
        serializer = ResourceSerializer(
            data=self.serializer_data(
                Resource.ResourceType.PDF,
                SimpleUploadedFile("notes.pdf", b"%PDF-1.7\nvalid", content_type="text/html"),
            )
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("content type is not allowed", str(serializer.errors["file"][0]))

    @override_settings(RESOURCE_MAX_FILE_SIZE_BYTES=4)
    def test_rejects_oversized_file(self):
        serializer = ResourceSerializer(
            data=self.serializer_data(Resource.ResourceType.PDF, self.pdf_file(content=b"%PDF-1.7"))
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("maximum allowed size", str(serializer.errors["file"][0]))

    def test_rejects_resource_type_and_file_mismatch(self):
        serializer = ResourceSerializer(
            data=self.serializer_data(
                Resource.ResourceType.PDF,
                SimpleUploadedFile("assignment.docx", b"not-a-docx", content_type="application/octet-stream"),
            )
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("file", serializer.errors)

    def test_link_resources_reject_uploaded_files(self):
        serializer = ResourceSerializer(
            data={
                "title": "External resource",
                "subject": "Physics",
                "resource_type": Resource.ResourceType.LINK,
                "external_url": "https://example.com/resource",
                "file": self.pdf_file(),
            }
        )

        self.assertFalse(serializer.is_valid())
        self.assertEqual(str(serializer.errors["file"][0]), "Link resources cannot include an uploaded file.")

    def test_link_resource_without_file_is_valid(self):
        serializer = ResourceSerializer(
            data={
                "title": "External resource",
                "subject": "Physics",
                "resource_type": Resource.ResourceType.LINK,
                "external_url": "https://example.com/resource",
            }
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_metadata_only_existing_resource_behavior_remains_valid(self):
        serializer = ResourceSerializer(
            data=self.serializer_data(Resource.ResourceType.NOTES)
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_unauthorized_upload_and_update_are_rejected(self):
        owner = self._create_user("resource-owner")
        other_user = self._create_user("resource-other")
        resource = Resource.objects.create(
            title="Existing resource",
            uploader=owner,
            subject="Physics",
            resource_type=Resource.ResourceType.PDF,
            status=PublicationStatus.PUBLISHED,
        )
        client = APIClient()

        unauthenticated = client.post(
            "/api/resources/",
            self.serializer_data(Resource.ResourceType.PDF, self.pdf_file()),
            format="multipart",
        )
        client.force_authenticate(user=other_user)
        unauthorized_update = client.patch(
            f"/api/resources/{resource.pk}/",
            {"file": self.pdf_file("replacement.pdf")},
            format="multipart",
        )

        self.assertEqual(unauthenticated.status_code, 401)
        self.assertEqual(unauthorized_update.status_code, 403)
        resource.refresh_from_db()
        self.assertFalse(resource.file)


    def test_retried_resource_create_returns_the_original_resource(self):
        owner = self._create_user("retry-owner")
        client = APIClient()
        client.force_authenticate(user=owner)
        upload_id = str(uuid4())
        payload = {
            "title": "Retry-safe resource",
            "subject": "Physics",
            "resource_type": Resource.ResourceType.NOTES,
        }

        first = client.post("/api/resources/", payload, format="json", HTTP_X_UPLOAD_ID=upload_id)
        second = client.post("/api/resources/", payload, format="json", HTTP_X_UPLOAD_ID=upload_id)

        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 201)
        self.assertEqual(first.data["id"], second.data["id"])
        self.assertEqual(Resource.objects.filter(client_upload_id=upload_id).count(), 1)
        self.assertEqual(first.data["status"], PublicationStatus.PUBLISHED)

    @staticmethod
    def _create_user(username: str):
        from django.contrib.auth.models import User

        return User.objects.create_user(username=username, password="not-used-in-test")


class VideoPublishingTests(TestCase):
    def test_video_upload_is_published_and_listed(self):
        owner = User.objects.create_user("video-owner", password="not-used-in-test")
        client = APIClient()
        client.force_authenticate(user=owner)

        response = client.post(
            "/api/videos/",
            {
                "title": "Published video",
                "description": "A test video",
                "subject": "Physics",
                "topic": "Motion",
                "youtube_url": "https://www.youtube.com/watch?v=I9R9BhhuPlY",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201, response.data)
        video = Video.objects.get(pk=response.data["id"])
        self.assertEqual(video.status, PublicationStatus.PUBLISHED)

        listed = APIClient().get("/api/videos/")

        self.assertEqual(listed.status_code, 200, listed.data)
        self.assertEqual([item["id"] for item in listed.data["results"]], [video.pk])


class CloudinaryUploadServiceTests(TestCase):
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
        "STORAGES": {
            "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
            "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
            "cloudinary_media": {"BACKEND": "cloudinary_storage.storage.RawMediaCloudinaryStorage"},
        },
    }

    @override_settings(**cloudinary_settings)
    @patch("cloudinary.uploader.upload")
    def test_valid_file_reaches_cloudinary_and_stores_reference(self, upload_mock):
        owner = User.objects.create_user(username="cloud-owner", password="not-used-in-test")
        upload_mock.return_value = {
            "public_id": "studymate/resources/pdf/uploader-1/asset.pdf",
        }
        serializer = ResourceSerializer(
            data={
                "title": "Cloud resource",
                "subject": "Physics",
                "resource_type": Resource.ResourceType.PDF,
                "file": SimpleUploadedFile("notes.pdf", b"%PDF-1.7\nvalid", content_type="application/pdf"),
            }
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        resource = serializer.save(uploader=owner)

        upload_mock.assert_called_once()
        self.assertIn("studymate/resources/pdf/uploader-", upload_mock.call_args.kwargs["folder"])
        self.assertEqual(upload_mock.call_args.kwargs["resource_type"], "raw")
        self.assertEqual(resource.uploader, owner)
        self.assertEqual(resource.file.name, "cloudinary://studymate/resources/pdf/uploader-1/asset.pdf")
        representation = ResourceSerializer(resource).data
        self.assertIn("https://api.cloudinary.com/v1_1/test-cloud/raw/download?", representation["file"])
        self.assertIn("public_id=studymate%2Fresources%2Fpdf%2Fuploader-1%2Fasset.pdf", representation["file"])
        self.assertNotIn("test-secret", representation["file"])

    def test_cloudinary_storage_name_cannot_escape_configured_folder(self):
        storage_name = _storage_name(
            resource_type="../pdf",
            uploader_id=7,
            extension=".pdf",
        )

        self.assertTrue(storage_name.startswith("studymate/resources/"))
        self.assertIn("/uploader-7/", storage_name)
        self.assertNotIn("..", storage_name)
        self.assertNotIn("\\", storage_name)

    @override_settings(**cloudinary_settings)
    @patch("cloudinary.uploader.upload")
    def test_invalid_file_is_rejected_before_cloudinary(self, upload_mock):
        serializer = ResourceSerializer(
            data={
                "title": "Invalid cloud resource",
                "subject": "Physics",
                "resource_type": Resource.ResourceType.PDF,
                "file": SimpleUploadedFile("notes.pdf", b"not-a-pdf", content_type="application/pdf"),
            }
        )

        self.assertFalse(serializer.is_valid())
        upload_mock.assert_not_called()

    @override_settings(**cloudinary_settings)
    @patch("cloudinary.uploader.upload", side_effect=RuntimeError("provider failure"))
    def test_cloudinary_failure_returns_safe_validation_error_without_record(self, upload_mock):
        owner = User.objects.create_user(username="failed-cloud-owner", password="not-used-in-test")
        serializer = ResourceSerializer(
            data={
                "title": "Failed cloud resource",
                "subject": "Physics",
                "resource_type": Resource.ResourceType.PDF,
                "file": SimpleUploadedFile("notes.pdf", b"%PDF-1.7\nvalid", content_type="application/pdf"),
            }
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        with self.assertRaises(serializers.ValidationError) as raised:
            serializer.save(uploader=owner)

        upload_mock.assert_called_once()
        self.assertEqual(Resource.objects.count(), 0)
        self.assertNotIn("provider failure", str(raised.exception))
        self.assertNotIn("test-secret", str(raised.exception))

    @override_settings(**cloudinary_settings)
    @patch("cloudinary.uploader.upload")
    def test_api_uses_authenticated_owner_not_frontend_owner(self, upload_mock):
        owner = User.objects.create_user(username="request-owner", password="not-used-in-test")
        other_user = User.objects.create_user(username="frontend-owner", password="not-used-in-test")
        upload_mock.return_value = {
            "public_id": "studymate/resources/pdf/uploader-1/owned.pdf",
        }
        client = APIClient()
        client.force_authenticate(user=owner)

        response = client.post(
            "/api/resources/",
            {
                "title": "Owned cloud resource",
                "subject": "Physics",
                "resource_type": Resource.ResourceType.PDF,
                "uploader": other_user.pk,
                "user_id": other_user.pk,
                "file": SimpleUploadedFile("owned.pdf", b"%PDF-1.7\nvalid", content_type="application/pdf"),
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(Resource.objects.get(pk=response.data["id"]).uploader, owner)
        self.assertNotIn("CLOUDINARY_API_SECRET", response.data)
        self.assertNotIn("test-secret", str(response.data))

    @override_settings(**cloudinary_settings)
    @patch("cloudinary.uploader.destroy")
    @patch("cloudinary.uploader.upload")
    def test_successful_file_replacement_cleans_old_media_after_commit(self, upload_mock, destroy_mock):
        owner = User.objects.create_user(username="replacement-owner", password="not-used-in-test")
        resource = Resource.objects.create(
            title="Replaceable resource",
            uploader=owner,
            subject="Physics",
            resource_type=Resource.ResourceType.PDF,
            file="cloudinary://studymate/resources/pdf/uploader-1/old.pdf",
        )
        upload_mock.return_value = {
            "public_id": "studymate/resources/pdf/uploader-1/new.pdf",
        }
        destroy_mock.return_value = {"result": "ok"}
        serializer = ResourceSerializer(
            instance=resource,
            data={"file": SimpleUploadedFile("new.pdf", b"%PDF-1.7\nnew", content_type="application/pdf")},
            partial=True,
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        with self.captureOnCommitCallbacks(execute=True):
            updated_resource = serializer.save()

        resource.refresh_from_db()
        self.assertEqual(updated_resource.file.name, "cloudinary://studymate/resources/pdf/uploader-1/new.pdf")
        self.assertEqual(resource.file.name, updated_resource.file.name)
        destroy_mock.assert_called_once_with(
            "studymate/resources/pdf/uploader-1/old.pdf",
            invalidate=True,
            resource_type="raw",
        )

    @override_settings(**cloudinary_settings)
    @patch("cloudinary.uploader.destroy")
    @patch("cloudinary.uploader.upload")
    def test_shared_cloudinary_reference_is_not_deleted(self, upload_mock, destroy_mock):
        owner = User.objects.create_user(username="shared-owner", password="not-used-in-test")
        shared_reference = "cloudinary://studymate/resources/pdf/uploader-1/shared.pdf"
        resource = Resource.objects.create(
            title="Shared source",
            uploader=owner,
            subject="Physics",
            resource_type=Resource.ResourceType.PDF,
            file=shared_reference,
        )
        Resource.objects.create(
            title="Shared copy",
            uploader=owner,
            subject="Physics",
            resource_type=Resource.ResourceType.PDF,
            file=shared_reference,
        )
        upload_mock.return_value = {
            "public_id": "studymate/resources/pdf/uploader-1/new.pdf",
        }
        serializer = ResourceSerializer(
            instance=resource,
            data={"file": SimpleUploadedFile("new.pdf", b"%PDF-1.7\nnew", content_type="application/pdf")},
            partial=True,
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        with self.captureOnCommitCallbacks(execute=True):
            serializer.save()

        destroy_mock.assert_not_called()

    @override_settings(**cloudinary_settings)
    @patch("cloudinary.uploader.destroy")
    @patch("cloudinary.uploader.upload")
    def test_failed_replacement_preserves_existing_resource_and_cleans_new_media(self, upload_mock, destroy_mock):
        owner = User.objects.create_user(username="failed-replacement-owner", password="not-used-in-test")
        resource = Resource.objects.create(
            title="Protected resource",
            uploader=owner,
            subject="Physics",
            resource_type=Resource.ResourceType.PDF,
            file="cloudinary://studymate/resources/pdf/uploader-1/old.pdf",
        )
        upload_mock.return_value = {
            "public_id": "studymate/resources/pdf/uploader-1/new.pdf",
        }
        destroy_mock.return_value = {"result": "ok"}
        serializer = ResourceSerializer(
            instance=resource,
            data={"file": SimpleUploadedFile("new.pdf", b"%PDF-1.7\nnew", content_type="application/pdf")},
            partial=True,
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        with patch.object(Resource, "save", side_effect=RuntimeError("database failure")):
            with self.assertRaises(RuntimeError):
                serializer.save()

        resource.refresh_from_db()
        self.assertEqual(resource.file.name, "cloudinary://studymate/resources/pdf/uploader-1/old.pdf")
        destroy_mock.assert_called_once_with(
            "studymate/resources/pdf/uploader-1/new.pdf",
            invalidate=True,
            resource_type="raw",
        )

    @override_settings(**cloudinary_settings)
    @patch("cloudinary.uploader.upload")
    def test_owner_can_update_metadata_without_replacing_media(self, upload_mock):
        owner = User.objects.create_user(username="metadata-owner", password="not-used-in-test")
        resource = Resource.objects.create(
            title="Original title",
            uploader=owner,
            subject="Physics",
            resource_type=Resource.ResourceType.PDF,
            file="cloudinary://studymate/resources/pdf/uploader-1/existing.pdf",
        )
        client = APIClient()
        client.force_authenticate(user=owner)

        response = client.patch(
            f"/api/resources/{resource.pk}/",
            {"title": "Updated title"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["title"], "Updated title")
        self.assertEqual(Resource.objects.get(pk=resource.pk).file.name, resource.file.name)
        upload_mock.assert_not_called()

    @override_settings(**cloudinary_settings)
    @patch("cloudinary.uploader.upload")
    def test_non_owner_cannot_replace_media(self, upload_mock):
        owner = User.objects.create_user(username="protected-owner", password="not-used-in-test")
        other_user = User.objects.create_user(username="replacement-other", password="not-used-in-test")
        resource = Resource.objects.create(
            title="Protected resource",
            uploader=owner,
            subject="Physics",
            resource_type=Resource.ResourceType.PDF,
            status=PublicationStatus.PUBLISHED,
            file="cloudinary://studymate/resources/pdf/uploader-1/existing.pdf",
        )
        client = APIClient()
        client.force_authenticate(user=other_user)

        response = client.patch(
            f"/api/resources/{resource.pk}/",
            {"file": SimpleUploadedFile("replacement.pdf", b"%PDF-1.7\nnew", content_type="application/pdf")},
            format="multipart",
        )

        self.assertEqual(response.status_code, 403)
        upload_mock.assert_not_called()
        self.assertEqual(Resource.objects.get(pk=resource.pk).file.name, resource.file.name)

    @override_settings(**cloudinary_settings)
    @patch("cloudinary.uploader.destroy")
    def test_owner_delete_cleans_cloudinary_media_after_commit(self, destroy_mock):
        owner = User.objects.create_user(username="delete-owner", password="not-used-in-test")
        resource = Resource.objects.create(
            title="Deletable cloud resource",
            uploader=owner,
            subject="Physics",
            resource_type=Resource.ResourceType.PDF,
            status=PublicationStatus.PUBLISHED,
            file="cloudinary://studymate/resources/pdf/uploader-1/delete.pdf",
        )
        destroy_mock.return_value = {"result": "ok"}
        client = APIClient()
        client.force_authenticate(user=owner)

        with self.captureOnCommitCallbacks(execute=True):
            response = client.delete(f"/api/resources/{resource.pk}/")

        self.assertEqual(response.status_code, 204)
        self.assertFalse(Resource.objects.filter(pk=resource.pk).exists())
        destroy_mock.assert_called_once_with(
            "studymate/resources/pdf/uploader-1/delete.pdf",
            invalidate=True,
            resource_type="raw",
        )

    @override_settings(**cloudinary_settings)
    @patch("cloudinary.uploader.destroy")
    def test_non_owner_delete_preserves_resource_and_media(self, destroy_mock):
        owner = User.objects.create_user(username="delete-protected-owner", password="not-used-in-test")
        other_user = User.objects.create_user(username="delete-protected-other", password="not-used-in-test")
        resource = Resource.objects.create(
            title="Protected cloud resource",
            uploader=owner,
            subject="Physics",
            resource_type=Resource.ResourceType.PDF,
            status=PublicationStatus.PUBLISHED,
            file="cloudinary://studymate/resources/pdf/uploader-1/protected.pdf",
        )
        client = APIClient()
        client.force_authenticate(user=other_user)

        response = client.delete(f"/api/resources/{resource.pk}/")

        self.assertEqual(response.status_code, 403)
        self.assertTrue(Resource.objects.filter(pk=resource.pk).exists())
        destroy_mock.assert_not_called()
