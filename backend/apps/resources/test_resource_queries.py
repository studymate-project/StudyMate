from django.contrib.auth.models import User
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient

from apps.interactions.models import ResourceRating, ResourceUpvote, SavedResource

from .models import PublicationStatus, Resource, ResourceDownload, ResourceView


class ResourceMetricQueryTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="resource-query-user",
            password="not-used-in-test",
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def create_resource(self, title):
        return Resource.objects.create(
            title=title,
            subject="Physics",
            resource_type=Resource.ResourceType.NOTES,
            uploader=self.user,
            status=PublicationStatus.PUBLISHED,
        )

    def add_metrics(self, resource, *, offset=0):
        for _ in range(offset + 1):
            ResourceView.objects.create(resource=resource, user=self.user)
            ResourceDownload.objects.create(resource=resource, user=self.user)
        SavedResource.objects.create(resource=resource, user=self.user)
        ResourceUpvote.objects.create(resource=resource, user=self.user)
        ResourceRating.objects.create(resource=resource, user=self.user, rating=4)

    def test_resource_list_metric_queries_do_not_grow_with_resources_or_events(self):
        first_resource = self.create_resource("First resource")
        self.add_metrics(first_resource)

        with CaptureQueriesContext(connection) as small_queries:
            small_response = self.client.get("/api/resources/")

        self.assertEqual(small_response.status_code, 200)
        first_data = next(
            item for item in small_response.data["results"] if item["title"] == "First resource"
        )
        self.assertEqual(first_data["views"], 1)
        self.assertEqual(first_data["downloads"], 1)
        self.assertEqual(first_data["saves"], 1)
        self.assertEqual(first_data["upvotes"], 1)
        self.assertEqual(first_data["rating"], 4.0)
        self.assertEqual(first_data["rating_count"], 1)
        self.assertEqual(first_data["user_rating"], 4)
        self.assertTrue(first_data["is_saved"])

        for index in range(2):
            resource = self.create_resource(f"Additional resource {index}")
            self.add_metrics(resource, offset=2)

        with CaptureQueriesContext(connection) as large_queries:
            large_response = self.client.get("/api/resources/")

        self.assertEqual(large_response.status_code, 200)
        self.assertEqual(len(large_response.data["results"]), 3)
        self.assertEqual(
            len(large_queries),
            len(small_queries),
            "resource metric serialization should not add one query per resource or event",
        )
