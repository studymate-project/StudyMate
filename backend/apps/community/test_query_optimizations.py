from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from apps.interactions.models import QuestionUpvote

from .models import Answer, Question


class QuestionListQueryOptimizationTests(TestCase):
    def test_question_list_returns_independent_relationship_counts(self):
        author = User.objects.create_user(username="question-query-owner", password="not-used-in-test")
        voters = [
            User.objects.create_user(username=f"question-query-voter-{index}", password="not-used-in-test")
            for index in range(2)
        ]
        question = Question.objects.create(
            title="Counted question",
            body="Question body",
            author=author,
            subject="Physics",
        )
        for voter in voters:
            QuestionUpvote.objects.create(user=voter, question=question)
        for index in range(3):
            Answer.objects.create(
                question=question,
                author=author,
                body=f"Answer {index}",
            )

        response = APIClient().get("/api/questions/")

        self.assertEqual(response.status_code, 200, response.data)
        result = next(item for item in response.data["results"] if item["id"] == question.pk)
        self.assertEqual(result["upvotes"], 2)
        self.assertEqual(result["answers"], 3)
