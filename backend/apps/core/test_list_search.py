from datetime import timedelta

from django.contrib.auth.models import User
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework.test import APIClient

from apps.community.models import Question
from apps.resources.models import PublicationStatus, Resource, Tag, Video


class ListSearchAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.owner = User.objects.create_user(username="list-search-owner", password="not-used-in-test")
        self.other_user = User.objects.create_user(username="list-search-other", password="not-used-in-test")

    def create_resource(self, **overrides):
        values = {
            "title": "List search resource",
            "uploader": self.owner,
            "subject": "Computer Science",
            "resource_type": Resource.ResourceType.NOTES,
            "status": PublicationStatus.PUBLISHED,
        }
        values.update(overrides)
        return Resource.objects.create(**values)

    def create_video(self, **overrides):
        values = {
            "title": "List search video",
            "uploader": self.owner,
            "youtube_video_id": f"V{Video.objects.count():010d}",
            "subject": "Computer Science",
            "status": PublicationStatus.PUBLISHED,
        }
        values.update(overrides)
        return Video.objects.create(**values)

    def create_question(self, **overrides):
        values = {
            "title": "List search question",
            "body": "A list search question body.",
            "author": self.owner,
            "subject": "Computer Science",
            "status": PublicationStatus.PUBLISHED,
        }
        values.update(overrides)
        return Question.objects.create(**values)

    @staticmethod
    def result_ids(response):
        return [item["id"] for item in response.data["results"]]

    def test_video_search_matches_current_content_fields_and_excludes_non_matches(self):
        matches = [
            self.create_video(title="vidsearch title"),
            self.create_video(description="vidsearch description"),
            self.create_video(subject="vidsearch subject"),
            self.create_video(topic="vidsearch topic"),
            self.create_video(course="vidsearch course"),
            self.create_video(semester="vidsearch semester"),
        ]
        tagged = self.create_video(title="Tagged video")
        tagged.tags.add(Tag.objects.create(name="Vidsearch tag", slug="vidsearch-tag"))
        non_match = self.create_video(title="Unrelated lecture", description="Different content")

        response = self.client.get("/api/videos/", {"search": "VIDSEARCH"})

        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["count"], len(matches) + 1)
        self.assertEqual(set(self.result_ids(response)), {video.pk for video in matches} | {tagged.pk})
        self.assertNotIn(non_match.pk, self.result_ids(response))

    def test_video_search_preserves_pagination_and_default_ordering(self):
        videos = [self.create_video(title=f"paged vidsearch video {index}") for index in range(21)]
        base_time = timezone.now()
        for index, video in enumerate(videos):
            Video.objects.filter(pk=video.pk).update(created_at=base_time + timedelta(seconds=index))

        first_page = self.client.get("/api/videos/", {"search": "vidsearch", "page": 1})
        second_page = self.client.get("/api/videos/", {"search": "vidsearch", "page": 2})

        self.assertEqual(first_page.status_code, 200, first_page.data)
        self.assertEqual(second_page.status_code, 200, second_page.data)
        self.assertEqual(first_page.data["count"], len(videos))
        self.assertEqual(len(first_page.data["results"]), 20)
        self.assertEqual(len(second_page.data["results"]), 1)
        self.assertEqual(self.result_ids(first_page)[0], videos[-1].pk)
        self.assertEqual(self.result_ids(second_page)[0], videos[0].pk)
        self.assertTrue(set(self.result_ids(first_page)).isdisjoint(self.result_ids(second_page)))

    def test_video_ordering_uses_primary_key_to_break_created_at_ties(self):
        videos = [self.create_video(title=f"tied video {index}") for index in range(21)]
        tied_time = timezone.now()
        Video.objects.filter(pk__in=[video.pk for video in videos]).update(created_at=tied_time)

        first_page = self.client.get("/api/videos/", {"page": 1})
        second_page = self.client.get("/api/videos/", {"page": 2})

        self.assertEqual(first_page.status_code, 200, first_page.data)
        self.assertEqual(second_page.status_code, 200, second_page.data)
        expected_ids = [video.pk for video in reversed(videos)]
        self.assertEqual(self.result_ids(first_page), expected_ids[:20])
        self.assertEqual(self.result_ids(second_page), expected_ids[20:])

    def test_video_search_preserves_visibility_boundaries(self):
        public_video = self.create_video(
            title="visibility vidsearch public",
            uploader=self.other_user,
        )
        owner_draft = self.create_video(
            title="visibility vidsearch owner draft",
            status=PublicationStatus.DRAFT,
        )
        other_draft = self.create_video(
            title="visibility vidsearch other draft",
            uploader=self.other_user,
            status=PublicationStatus.DRAFT,
        )

        anonymous = self.client.get("/api/videos/", {"search": "visibility vidsearch"})
        self.client.force_authenticate(user=self.owner)
        owner = self.client.get("/api/videos/", {"search": "visibility vidsearch"})
        self.client.force_authenticate(user=self.other_user)
        other = self.client.get("/api/videos/", {"search": "visibility vidsearch"})

        self.assertEqual(anonymous.status_code, 200)
        self.assertEqual(owner.status_code, 200)
        self.assertEqual(other.status_code, 200)
        self.assertEqual(self.result_ids(anonymous), [public_video.pk])
        self.assertEqual(set(self.result_ids(owner)), {public_video.pk, owner_draft.pk})
        self.assertEqual(set(self.result_ids(other)), {public_video.pk, other_draft.pk})

    def test_list_search_omits_blank_values_and_rejects_overlong_values_consistently(self):
        endpoints = (
            ("/api/resources/", self.create_resource(title="shared list search")),
            ("/api/videos/", self.create_video(title="shared list search")),
            ("/api/questions/", self.create_question(title="shared list search")),
        )

        for path, instance in endpoints:
            with self.subTest(path=path):
                omitted = self.client.get(path)
                whitespace = self.client.get(path, {"search": "  \t  "})
                normalized = self.client.get(path, {"search": "  shared   list search  "})
                at_limit = self.client.get(path, {"search": "x" * 200})
                too_long = self.client.get(path, {"search": "x" * 201})

                self.assertEqual(omitted.status_code, 200)
                self.assertEqual(whitespace.status_code, 200)
                self.assertEqual(whitespace.data["count"], omitted.data["count"])
                self.assertEqual(normalized.status_code, 200)
                self.assertEqual(self.result_ids(normalized), [instance.pk])
                self.assertEqual(at_limit.status_code, 200)
                self.assertEqual(too_long.status_code, 400, too_long.data)
                self.assertIn("search", too_long.data)

    def test_resource_and_question_search_remain_compatible(self):
        resource = self.create_resource(title="Compatible Java resource")
        question = self.create_question(title="Compatible Java question")

        resource_response = self.client.get("/api/resources/", {"search": " java "})
        question_response = self.client.get("/api/questions/", {"search": " java "})

        self.assertEqual(resource_response.status_code, 200)
        self.assertEqual(question_response.status_code, 200)
        self.assertIn(resource.pk, self.result_ids(resource_response))
        self.assertIn(question.pk, self.result_ids(question_response))

    def test_list_search_query_counts_do_not_grow_with_result_rows(self):
        cases = (
            ("/api/resources/", self.create_resource, "resource-query-count"),
            ("/api/videos/", self.create_video, "video-query-count"),
            ("/api/questions/", self.create_question, "question-query-count"),
        )

        for path, factory, term in cases:
            with self.subTest(path=path):
                factory(title=f"{term} first")
                with CaptureQueriesContext(connection) as small_queries:
                    small_response = self.client.get(path, {"search": term})

                for index in range(20):
                    factory(title=f"{term} additional {index}")
                with CaptureQueriesContext(connection) as large_queries:
                    large_response = self.client.get(path, {"search": term})

                self.assertEqual(small_response.status_code, 200, small_response.data)
                self.assertEqual(large_response.status_code, 200, large_response.data)
                self.assertEqual(len(small_queries), len(large_queries))
