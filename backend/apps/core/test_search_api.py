from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.community.models import Question
from apps.resources.models import PublicationStatus, Resource, Tag, Video
from apps.users.models import StudentProfile


class UnifiedSearchAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="unified-search-user",
            password="not-used-in-test",
        )
        self.other_user = User.objects.create_user(
            username="unified-search-peer",
            password="not-used-in-test",
        )

    def create_resource(self, *, user=None, status=PublicationStatus.PUBLISHED, **overrides):
        values = {
            "title": "Search resource",
            "description": "A searchable resource description.",
            "uploader": user or self.user,
            "subject": "Computer Science",
            "resource_type": Resource.ResourceType.NOTES,
            "status": status,
        }
        values.update(overrides)
        return Resource.objects.create(**values)

    def create_video(self, *, user=None, status=PublicationStatus.PUBLISHED, **overrides):
        values = {
            "title": "Search video",
            "description": "A searchable video description.",
            "uploader": user or self.user,
            "youtube_video_id": f"S{Video.objects.count():010d}"[-11:],
            "subject": "Computer Science",
            "status": status,
        }
        values.update(overrides)
        return Video.objects.create(**values)

    def create_question(self, *, user=None, status=PublicationStatus.PUBLISHED, **overrides):
        values = {
            "title": "Search question",
            "body": "A searchable question body.",
            "author": user or self.user,
            "subject": "Computer Science",
            "status": status,
        }
        values.update(overrides)
        return Question.objects.create(**values)

    def test_search_combines_content_types_and_supports_tag_and_text_matches(self):
        resource = self.create_resource(
            title="Algorithms notes",
            description="Python data structures and examples.",
        )
        video = self.create_video(title="Python algorithms lecture")
        question = self.create_question(
            title="How should I practice algorithms?",
            body="Which Python algorithm should I learn first?",
        )
        tagged_resource = self.create_resource(title="Algorithms reference", description="Reference material")
        tag = Tag.objects.create(name="Python", slug="python")
        tagged_resource.tags.add(tag)

        response = self.client.get("/api/search/?q=python")

        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["query"], "python")
        self.assertEqual(
            {result["type"] for result in response.data["results"]},
            {"resource", "video", "question"},
        )
        result_ids = {(result["type"], result["id"]) for result in response.data["results"]}
        self.assertIn(("resource", resource.pk), result_ids)
        self.assertIn(("resource", tagged_resource.pk), result_ids)
        self.assertIn(("video", video.pk), result_ids)
        self.assertIn(("question", question.pk), result_ids)
        self.assertEqual(len(result_ids), len(response.data["results"]))

        resource_result = next(
            result
            for result in response.data["results"]
            if result["type"] == "resource" and result["id"] == resource.pk
        )
        self.assertEqual(resource_result["detail_url"], f"/api/resources/{resource.slug}/")
        self.assertIn("python", resource_result["snippet"].casefold())
        self.assertIn("subject", resource_result["metadata"])
        self.assertGreaterEqual(resource_result["score"], 0)

    def test_search_includes_public_user_profiles_without_exposing_private_identity_fields(self):
        StudentProfile.objects.create(
            user=self.user,
            display_name="Python Mentor",
            bio="Helps students with Python algorithms.",
        )

        response = self.client.get("/api/search/?q=python")

        self.assertEqual(response.status_code, 200, response.data)
        user_result = next(result for result in response.data["results"] if result["type"] == "user")
        self.assertEqual(user_result["id"], self.user.pk)
        self.assertEqual(user_result["title"], "Python Mentor")
        self.assertEqual(user_result["metadata"], {"username": self.user.username})
        self.assertEqual(user_result["detail_url"], f"/api/users/{self.user.username}/")
        self.assertNotIn("email", user_result)

    def test_search_ranks_title_matches_and_orders_equal_results_deterministically(self):
        title_match = self.create_resource(title="rankingterm title match", description="Generic description")
        body_match = self.create_question(
            title="Generic question",
            body="rankingterm body match",
        )
        tied_lower = self.create_resource(title="rankingterm tied", description="same ranking")
        tied_higher = self.create_resource(title="rankingterm tied", description="same ranking")
        tied_created_at = timezone.now()
        Resource.objects.filter(pk__in=(tied_lower.pk, tied_higher.pk)).update(created_at=tied_created_at)

        response = self.client.get("/api/search/?q=rankingterm")

        self.assertEqual(response.status_code, 200, response.data)
        results = response.data["results"]
        title_index = next(
            index for index, result in enumerate(results) if (result["type"], result["id"]) == ("resource", title_match.pk)
        )
        body_index = next(
            index for index, result in enumerate(results) if (result["type"], result["id"]) == ("question", body_match.pk)
        )
        self.assertLess(title_index, body_index)
        tied_ids = [
            result["id"]
            for result in results
            if result["type"] == "resource" and result["id"] in {tied_lower.pk, tied_higher.pk}
        ]
        self.assertEqual(tied_ids, [tied_higher.pk, tied_lower.pk])

    def test_search_supports_trigram_typo_matches(self):
        resource = self.create_resource(title="Pyhton")

        response = self.client.get("/api/search/?q=python")

        self.assertEqual(response.status_code, 200, response.data)
        self.assertIn(
            ("resource", resource.pk),
            {(result["type"], result["id"]) for result in response.data["results"]},
        )

    def test_search_normalizes_query_and_rejects_invalid_bounds(self):
        resource = self.create_resource(title="Whitespace normalization term")

        normalized_response = self.client.get("/api/search/?q=%20%20Whitespace%20%20normalization%20term%20")
        missing_response = self.client.get("/api/search/")
        blank_response = self.client.get("/api/search/?q=%20%20")
        long_response = self.client.get(f"/api/search/?q={'x' * 201}")
        null_character_response = self.client.get("/api/search/?q=%00")
        invalid_limit_response = self.client.get("/api/search/?q=term&limit=not-a-number")
        invalid_offset_response = self.client.get("/api/search/?q=term&offset=-1")
        maximum_offset_response = self.client.get("/api/search/?q=term&offset=1000")
        over_maximum_offset_response = self.client.get("/api/search/?q=term&offset=1001")

        self.assertEqual(normalized_response.status_code, 200, normalized_response.data)
        self.assertEqual(normalized_response.data["query"], "Whitespace normalization term")
        self.assertIn(resource.pk, [result["id"] for result in normalized_response.data["results"]])
        self.assertEqual(missing_response.status_code, 400)
        self.assertIn("q", missing_response.data)
        self.assertEqual(blank_response.status_code, 400)
        self.assertIn("q", blank_response.data)
        self.assertEqual(long_response.status_code, 400)
        self.assertIn("q", long_response.data)
        self.assertEqual(null_character_response.status_code, 400)
        self.assertIn("q", null_character_response.data)
        self.assertEqual(invalid_limit_response.status_code, 400)
        self.assertIn("limit", invalid_limit_response.data)
        self.assertEqual(invalid_offset_response.status_code, 400)
        self.assertIn("offset", invalid_offset_response.data)
        self.assertEqual(maximum_offset_response.status_code, 200, maximum_offset_response.data)
        self.assertEqual(over_maximum_offset_response.status_code, 400)
        self.assertIn("offset", over_maximum_offset_response.data)

    def test_search_visibility_matches_existing_content_endpoints(self):
        public_resource = self.create_resource(title="visibilityterm public resource", user=self.other_user)
        own_private_resource = self.create_resource(
            title="visibilityterm own private resource",
            status=PublicationStatus.DRAFT,
        )
        other_private_resource = self.create_resource(
            title="visibilityterm other private resource",
            user=self.other_user,
            status=PublicationStatus.DRAFT,
        )
        public_video = self.create_video(title="visibilityterm public video", user=self.other_user)
        own_private_video = self.create_video(
            title="visibilityterm own private video",
            status=PublicationStatus.DRAFT,
        )
        other_private_video = self.create_video(
            title="visibilityterm other private video",
            user=self.other_user,
            status=PublicationStatus.DRAFT,
        )
        public_question = self.create_question(title="visibilityterm public question", user=self.other_user)
        own_private_question = self.create_question(
            title="visibilityterm own private question",
            status=PublicationStatus.DRAFT,
        )
        other_private_question = self.create_question(
            title="visibilityterm other private question",
            user=self.other_user,
            status=PublicationStatus.DRAFT,
        )

        anonymous_response = self.client.get("/api/search/?q=visibilityterm")
        self.client.force_authenticate(user=self.user)
        authenticated_response = self.client.get("/api/search/?q=visibilityterm")

        anonymous_ids = {(result["type"], result["id"]) for result in anonymous_response.data["results"]}
        authenticated_ids = {(result["type"], result["id"]) for result in authenticated_response.data["results"]}
        self.assertEqual(anonymous_response.status_code, 200)
        self.assertEqual(authenticated_response.status_code, 200)
        self.assertTrue(
            {("resource", public_resource.pk), ("video", public_video.pk), ("question", public_question.pk)}
            <= anonymous_ids
        )
        self.assertFalse(
            {("resource", own_private_resource.pk), ("resource", other_private_resource.pk),
             ("video", own_private_video.pk), ("video", other_private_video.pk),
             ("question", own_private_question.pk), ("question", other_private_question.pk)}
            & anonymous_ids
        )
        self.assertTrue(
            {("resource", public_resource.pk), ("resource", own_private_resource.pk),
             ("video", public_video.pk), ("video", own_private_video.pk),
             ("question", public_question.pk), ("question", own_private_question.pk)}
            <= authenticated_ids,
            authenticated_response.data,
        )
        self.assertFalse(
            {("resource", other_private_resource.pk), ("video", other_private_video.pk),
             ("question", other_private_question.pk)}
            & authenticated_ids
        )

    def test_search_limits_results_supports_offset_and_returns_no_results_cleanly(self):
        resources = [
            self.create_resource(title=f"boundedterm resource {index}")
            for index in range(5)
        ]

        first_response = self.client.get("/api/search/?q=boundedterm&limit=2")
        second_response = self.client.get("/api/search/?q=boundedterm&limit=2&offset=2")
        empty_response = self.client.get("/api/search/?q=term-that-does-not-exist")

        self.assertEqual(first_response.status_code, 200, first_response.data)
        self.assertEqual(len(first_response.data["results"]), 2)
        self.assertTrue(first_response.data["has_more"])
        self.assertEqual(first_response.data["next_offset"], 2)
        self.assertEqual(second_response.status_code, 200, second_response.data)
        self.assertEqual(len(second_response.data["results"]), 2)
        self.assertTrue(
            set(result["id"] for result in first_response.data["results"]).isdisjoint(
                result["id"] for result in second_response.data["results"]
            )
        )
        self.assertEqual(empty_response.status_code, 200)
        self.assertEqual(empty_response.data["results"], [])
        self.assertFalse(empty_response.data["has_more"])
        self.assertTrue(
            {result["id"] for result in first_response.data["results"] + second_response.data["results"]}
            <= {resource.pk for resource in resources}
        )

    def test_search_candidate_overfetch_keeps_late_global_pages_populated(self):
        for index in range(30):
            self.create_resource(title=f"overfetchterm resource {index}")
            self.create_video(title=f"overfetchterm video {index}")
            self.create_question(title=f"overfetchterm question {index}")

        response = self.client.get("/api/search/?q=overfetchterm&limit=5&offset=20")

        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(len(response.data["results"]), 5)
        self.assertTrue(response.data["has_more"])
        self.assertEqual(response.data["next_offset"], 25)
