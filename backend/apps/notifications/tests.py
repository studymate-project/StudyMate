from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.resources.models import Resource

from .models import Notification
from .services import create_notification


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
