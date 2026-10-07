from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from apps.community.models import Answer, Question
from apps.resources.models import PublicationStatus, Resource


User = get_user_model()


class ProfileFeedTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="profile-feed-user",
            email="profile-feed@example.com",
            password="not-used-in-test",
        )
        self.other_user = User.objects.create_user(
            username="profile-feed-other",
            email="profile-feed-other@example.com",
            password="not-used-in-test",
        )
        self.question = Question.objects.create(
            title="My question",
            body="Question body",
            author=self.user,
            subject="Physics",
        )
        self.other_question = Question.objects.create(
            title="Other question",
            body="Question body",
            author=self.other_user,
            subject="Physics",
        )
        self.answer = Answer.objects.create(
            question=self.other_question,
            author=self.user,
            body="My answer",
        )
        self.resource = Resource.objects.create(
            title="My resource",
            subject="Physics",
            resource_type=Resource.ResourceType.NOTES,
            uploader=self.user,
            status=PublicationStatus.PUBLISHED,
        )
        Resource.objects.create(
            title="Other resource",
            subject="Physics",
            resource_type=Resource.ResourceType.NOTES,
            uploader=self.other_user,
            status=PublicationStatus.PUBLISHED,
        )
        self.client.force_authenticate(user=self.user)

    def test_profile_feeds_are_bounded_and_scoped_to_the_requested_user(self):
        resources = self.client.get("/api/resources/", {"uploader": self.user.pk})
        questions = self.client.get("/api/questions/", {"author": self.user.pk})
        answers = self.client.get("/api/questions/answers/")

        self.assertEqual(resources.status_code, 200)
        self.assertEqual(questions.status_code, 200)
        self.assertEqual(answers.status_code, 200)
        self.assertEqual([item["id"] for item in resources.data["results"]], [self.resource.pk])
        self.assertEqual([item["id"] for item in questions.data["results"]], [self.question.pk])
        self.assertEqual([item["id"] for item in answers.data["results"]], [self.answer.pk])
        self.assertEqual(answers.data["results"][0]["question_title"], self.other_question.title)
        self.assertEqual(answers.data["results"][0]["question_slug"], self.other_question.slug)

    def test_invalid_profile_feed_filters_do_not_return_unbounded_data(self):
        self.assertEqual(self.client.get("/api/resources/", {"uploader": "invalid"}).data["results"], [])
        self.assertEqual(self.client.get("/api/questions/", {"author": "invalid"}).data["results"], [])
