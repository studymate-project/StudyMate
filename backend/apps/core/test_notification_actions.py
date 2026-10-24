from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from apps.community.models import Answer, Question
from apps.interactions.models import ResourceUpvote, SavedResource
from apps.notifications.models import Notification
from apps.resources.models import PublicationStatus, Resource


class NotificationActionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user(username="notification-owner", password="test-password")
        cls.actor = User.objects.create_user(username="notification-actor", password="test-password")
        cls.resource = Resource.objects.create(
            title="Notification resource",
            uploader=cls.owner,
            subject="Physics",
            resource_type=Resource.ResourceType.FILE,
            status=PublicationStatus.PUBLISHED,
        )
        cls.question = Question.objects.create(
            title="Notification question",
            body="Question body",
            author=cls.owner,
            subject="Physics",
        )
        cls.answer = Answer.objects.create(
            question=cls.question,
            author=cls.owner,
            body="Answer body",
        )

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(self.actor)

    def test_resource_save_and_upvote_create_owner_notifications_once(self):
        save_url = f"/api/resources/{self.resource.pk}/save/"
        upvote_url = f"/api/resources/{self.resource.pk}/upvote/"

        self.assertEqual(self.client.post(save_url).status_code, 201)
        self.assertEqual(self.client.post(save_url).status_code, 200)
        self.assertEqual(self.client.post(upvote_url).status_code, 201)
        self.assertEqual(self.client.post(upvote_url).status_code, 200)

        self.assertEqual(SavedResource.objects.filter(resource=self.resource).count(), 1)
        self.assertEqual(ResourceUpvote.objects.filter(resource=self.resource).count(), 1)
        self.assertEqual(
            Notification.objects.filter(
                recipient=self.owner,
                actor=self.actor,
                content_object=self.resource,
                notification_type=Notification.NotificationType.RESOURCE_SAVED,
            ).count(),
            1,
        )
        self.assertEqual(
            Notification.objects.filter(
                recipient=self.owner,
                actor=self.actor,
                content_object=self.resource,
                notification_type=Notification.NotificationType.RESOURCE_UPVOTED,
            ).count(),
            1,
        )

    def test_answer_upvote_and_follow_create_supported_notifications(self):
        answer_url = f"/api/questions/{self.question.pk}/answers/{self.answer.pk}/upvote/"
        follow_url = f"/api/users/{self.owner.username}/follow/"

        self.assertEqual(self.client.post(answer_url).status_code, 201)
        self.assertEqual(self.client.post(follow_url).status_code, 201)

        self.assertTrue(
            Notification.objects.filter(
                recipient=self.owner,
                actor=self.actor,
                notification_type=Notification.NotificationType.ANSWER_UPVOTED,
                content_object=self.answer,
            ).exists()
        )
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.owner,
                actor=self.actor,
                notification_type=Notification.NotificationType.NEW_FOLLOWER,
                content_object=self.actor,
            ).exists()
        )
