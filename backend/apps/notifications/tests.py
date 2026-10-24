from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import connection
from django.test import RequestFactory, TestCase
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient

from apps.resources.models import PublicationStatus, Resource, Video
from apps.community.models import Answer, Question

from .models import Notification
from .serializers import NotificationSerializer
from .services import create_notification
from .tasks import ensure_question_answer_notification_task


class NotificationServiceTests(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.recipient = User.objects.create_user(username="service-recipient", password="not-used-in-test")
        cls.actor = User.objects.create_user(username="service-actor", password="not-used-in-test")
        cls.resource = Resource.objects.create(
            title="Service resource",
            uploader=cls.actor,
            subject="Physics",
            resource_type=Resource.ResourceType.NOTES,
        )

    def test_create_notification_uses_server_derived_relationships_and_payload(self):
        notification = create_notification(
            recipient=self.recipient,
            actor=self.actor,
            notification_type=Notification.NotificationType.RESOURCE_SAVED,
            related_object=self.resource,
            payload={"resource_id": self.resource.pk, "source": "save"},
        )

        self.assertEqual(notification.recipient, self.recipient)
        self.assertEqual(notification.actor, self.actor)
        self.assertEqual(notification.notification_type, Notification.NotificationType.RESOURCE_SAVED)
        self.assertEqual(notification.content_object, self.resource)
        self.assertEqual(notification.payload, {"resource_id": self.resource.pk, "source": "save"})
        self.assertFalse(notification.is_read)

    def test_create_notification_defaults_optional_values(self):
        notification = create_notification(
            recipient=self.recipient,
            notification_type=Notification.NotificationType.SYSTEM,
        )

        self.assertIsNone(notification.actor)
        self.assertIsNone(notification.content_object)
        self.assertEqual(notification.payload, {})

    def test_create_notification_validates_required_and_trusted_values(self):
        with self.assertRaises(ValidationError):
            create_notification(
                recipient=None,
                notification_type=Notification.NotificationType.SYSTEM,
            )
        with self.assertRaises(ValidationError):
            create_notification(
                recipient=self.recipient,
                notification_type="not-supported",
            )
        with self.assertRaises(ValidationError):
            create_notification(
                recipient=self.recipient,
                notification_type=Notification.NotificationType.SYSTEM,
                payload=["not", "an", "object"],
            )

    def test_create_notification_rejects_unsupported_or_unsaved_related_objects(self):
        with self.assertRaises(ValidationError):
            create_notification(
                recipient=self.recipient,
                notification_type=Notification.NotificationType.SYSTEM,
                related_object=object(),
            )

        unsaved_resource = Resource(
            title="Unsaved resource",
            uploader=self.actor,
            subject="Physics",
            resource_type=Resource.ResourceType.NOTES,
        )
        with self.assertRaises(ValidationError):
            create_notification(
                recipient=self.recipient,
                notification_type=Notification.NotificationType.RESOURCE_SAVED,
                related_object=unsaved_resource,
            )

    def test_question_answer_notification_reuses_existing_event_record(self):
        question = Question.objects.create(
            title="Durable notification question",
            body="Question body",
            author=self.recipient,
            subject="Physics",
        )
        answer = Answer.objects.create(
            question=question,
            author=self.actor,
            body="Answer body",
        )

        first = create_notification(
            recipient=self.recipient,
            actor=self.actor,
            notification_type=Notification.NotificationType.QUESTION_ANSWERED,
            related_object=question,
            payload={"answer_id": answer.pk},
        )
        repeated = create_notification(
            recipient=self.recipient,
            actor=self.actor,
            notification_type=Notification.NotificationType.QUESTION_ANSWERED,
            related_object=question,
            payload={"answer_id": answer.pk},
        )

        self.assertEqual(repeated.pk, first.pk)
        self.assertEqual(Notification.objects.filter(pk=first.pk).count(), 1)

    def test_duplicate_notification_repair_tasks_create_one_event(self):
        question = Question.objects.create(
            title="Repair notification question",
            body="Question body",
            author=self.recipient,
            subject="Physics",
        )
        answer = Answer.objects.create(
            question=question,
            author=self.actor,
            body="Answer body",
        )

        ensure_question_answer_notification_task.run(answer.pk)
        ensure_question_answer_notification_task.run(answer.pk)

        notifications = Notification.objects.filter(
            recipient=self.recipient,
            actor=self.actor,
            notification_type=Notification.NotificationType.QUESTION_ANSWERED,
            object_id=question.pk,
            payload__answer_id=answer.pk,
        )
        self.assertEqual(notifications.count(), 1)

    def test_resource_targets_preserve_file_video_and_external_link_destinations(self):
        file_resource = Resource.objects.create(
            title="Public file",
            uploader=self.actor,
            subject="Physics",
            resource_type=Resource.ResourceType.FILE,
            status=PublicationStatus.PUBLISHED,
        )
        link_resource = Resource.objects.create(
            title="External resource",
            uploader=self.actor,
            subject="Physics",
            resource_type=Resource.ResourceType.LINK,
            external_url="https://example.edu/resource",
            status=PublicationStatus.PUBLISHED,
        )
        video = Video.objects.create(
            title="Public video",
            uploader=self.actor,
            subject="Physics",
            youtube_video_id="dQw4w9WgXcQ",
            status=PublicationStatus.PUBLISHED,
        )
        notifications = [
            Notification.objects.create(
                recipient=self.recipient,
                actor=self.actor,
                notification_type=Notification.NotificationType.RESOURCE_SAVED,
                content_object=target,
            )
            for target in (file_resource, video, link_resource)
        ]
        request = RequestFactory().get("/api/notifications/")
        request.user = self.recipient

        targets = [NotificationSerializer(item, context={"request": request}).data["target"] for item in notifications]

        self.assertEqual(targets[0], {"kind": "resource", "url": f"/resources/{file_resource.slug}", "resource_type": "file"})
        self.assertEqual(targets[1], {"kind": "video", "url": f"/videos/{video.slug}", "resource_type": "video"})
        self.assertEqual(targets[2], {"kind": "external", "url": "https://example.edu/resource", "resource_type": "link"})

    def test_private_deleted_or_malformed_resource_targets_are_unavailable(self):
        private_resource = Resource.objects.create(
            title="Private resource",
            uploader=self.actor,
            subject="Physics",
            resource_type=Resource.ResourceType.FILE,
        )
        malformed_link = Resource.objects.create(
            title="Malformed link",
            uploader=self.actor,
            subject="Physics",
            resource_type=Resource.ResourceType.LINK,
            external_url="javascript:alert(1)",
            status=PublicationStatus.PUBLISHED,
        )
        private_notification = Notification.objects.create(
            recipient=self.recipient,
            actor=self.actor,
            notification_type=Notification.NotificationType.RESOURCE_SAVED,
            content_object=private_resource,
        )
        malformed_notification = Notification.objects.create(
            recipient=self.recipient,
            actor=self.actor,
            notification_type=Notification.NotificationType.RESOURCE_SAVED,
            content_object=malformed_link,
        )
        private_resource.delete()
        request = RequestFactory().get("/api/notifications/")
        request.user = self.recipient

        private_target = NotificationSerializer(private_notification, context={"request": request}).data["target"]
        malformed_target = NotificationSerializer(malformed_notification, context={"request": request}).data["target"]

        self.assertIsNone(private_target)
        self.assertIsNone(malformed_target)

    def test_video_is_an_allowed_related_notification_object(self):
        video = Video.objects.create(
            title="Service video",
            uploader=self.actor,
            subject="Physics",
            youtube_video_id="LmNoPqRsTuV",
            status=PublicationStatus.PUBLISHED,
        )

        notification = create_notification(
            recipient=self.recipient,
            actor=self.actor,
            notification_type=Notification.NotificationType.RESOURCE_UPVOTED,
            related_object=video,
        )

        self.assertEqual(notification.content_object, video)

    def test_notification_list_batches_generic_target_queries(self):
        client = APIClient()
        client.force_authenticate(user=self.recipient)

        resources = [
            Resource.objects.create(
                title=f"Batched resource {index}",
                uploader=self.actor,
                subject="Physics",
                resource_type=Resource.ResourceType.NOTES,
                status=PublicationStatus.PUBLISHED,
            )
            for index in range(3)
        ]

        Notification.objects.create(
            recipient=self.recipient,
            actor=self.actor,
            notification_type=Notification.NotificationType.RESOURCE_SAVED,
            content_object=resources[0],
        )
        with CaptureQueriesContext(connection) as one_notification_queries:
            one_response = client.get("/api/notifications/")

        for resource in resources[1:]:
            Notification.objects.create(
                recipient=self.recipient,
                actor=self.actor,
                notification_type=Notification.NotificationType.RESOURCE_SAVED,
                content_object=resource,
            )
        with CaptureQueriesContext(connection) as three_notification_queries:
            three_response = client.get("/api/notifications/")

        self.assertEqual(one_response.status_code, 200, one_response.data)
        self.assertEqual(three_response.status_code, 200, three_response.data)
        self.assertEqual(len(one_response.data["results"]), 1)
        self.assertEqual(len(three_response.data["results"]), 3)
        self.assertEqual(
            len(three_notification_queries),
            len(one_notification_queries),
            "generic notification targets should be loaded in batches, not once per notification",
        )
