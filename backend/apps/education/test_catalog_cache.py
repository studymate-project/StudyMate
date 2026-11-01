from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db import connection
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient

from apps.users.models import StudentProfile

from .cache import get_education_cache_version, set_cached_catalog_response
from .models import Course, EducationBackground, Interest, StudentInterest


TEST_CACHE_SETTINGS = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "education-catalog-tests",
    }
}


@override_settings(
    CACHES=TEST_CACHE_SETTINGS,
    EDUCATION_CATALOG_CACHE_TTL_SECONDS=3600,
    EDUCATION_CATALOG_CACHE_VERSION_TTL_SECONDS=86400,
)
class EducationCatalogCacheTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.background = EducationBackground.objects.create(
            name="Engineering",
            slug="cache-engineering",
        )
        cls.other_background = EducationBackground.objects.create(
            name="Commerce",
            slug="cache-commerce",
        )
        cls.course = Course.objects.create(
            education_background=cls.background,
            name="Computer Science",
            slug="cache-computer-science",
        )
        cls.other_course = Course.objects.create(
            education_background=cls.other_background,
            name="Accounting",
            slug="cache-accounting",
        )
        cls.interest = Interest.objects.create(
            name="Algorithms",
            slug="cache-algorithms",
        )

    def setUp(self):
        cache.clear()
        self.client = APIClient()

    def tearDown(self):
        cache.clear()

    def test_first_catalog_request_hits_database_and_second_request_is_cached(self):
        with CaptureQueriesContext(connection) as first_queries:
            first = self.client.get("/api/education/backgrounds/")
        with CaptureQueriesContext(connection) as second_queries:
            second = self.client.get("/api/education/backgrounds/")

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.data, second.data)
        self.assertGreater(len(first_queries), 0)
        self.assertEqual(len(second_queries), 0)

    def test_catalog_filters_have_separate_cache_entries(self):
        matching = self.client.get(
            "/api/education/courses/",
            {"background": self.background.pk},
        )
        other = self.client.get(
            "/api/education/courses/",
            {"background": self.other_background.pk},
        )

        self.assertEqual(matching.status_code, 200)
        self.assertEqual(other.status_code, 200)
        self.assertEqual(
            [course["id"] for course in matching.data["results"]],
            [self.course.pk],
        )
        self.assertEqual(
            [course["id"] for course in other.data["results"]],
            [self.other_course.pk],
        )

    def test_catalog_save_invalidates_cached_list_after_commit(self):
        initial = self.client.get("/api/education/backgrounds/")
        previous_version = get_education_cache_version()

        with self.captureOnCommitCallbacks(execute=True):
            with self.subTest("committed catalog mutation"):
                EducationBackground.objects.create(
                    name="Sciences",
                    slug="cache-sciences",
                )

        refreshed = self.client.get("/api/education/backgrounds/")

        self.assertEqual(initial.status_code, 200)
        self.assertEqual(refreshed.status_code, 200)
        self.assertNotEqual(get_education_cache_version(), previous_version)
        self.assertIn(
            "Sciences",
            {item["name"] for item in refreshed.data["results"]},
        )

    def test_catalog_m2m_change_invalidates_filtered_interest_list(self):
        filtered_url = "/api/education/interests/?course={}".format(self.course.pk)
        initial = self.client.get(filtered_url)
        self.assertEqual(initial.data["results"], [])

        with self.captureOnCommitCallbacks(execute=True):
            self.interest.courses.add(self.course)

        refreshed = self.client.get(filtered_url)
        self.assertEqual(refreshed.status_code, 200)
        self.assertEqual([item["id"] for item in refreshed.data["results"]], [self.interest.pk])

    def test_cache_failure_falls_back_to_database(self):
        with patch(
            "apps.education.cache.cache.get",
            side_effect=RuntimeError("cache unavailable"),
        ), patch(
            "apps.education.cache.cache.set",
            side_effect=RuntimeError("cache unavailable"),
        ), patch(
            "rest_framework.throttling.SimpleRateThrottle.allow_request",
            return_value=True,
        ):
            response = self.client.get("/api/education/backgrounds/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Engineering", {item["name"] for item in response.data["results"]})

    def test_cache_writes_use_configured_catalog_ttl(self):
        with patch("apps.education.cache.cache.set") as cache_set:
            set_cached_catalog_response("catalog-key", {"results": []})

        self.assertEqual(cache_set.call_args.kwargs["timeout"], 3600)

    def test_user_specific_student_interests_are_not_shared_catalog_cache_data(self):
        user_model = get_user_model()
        first_user = user_model.objects.create_user(username="catalog-private-one")
        second_user = user_model.objects.create_user(username="catalog-private-two")
        first_profile = StudentProfile.objects.create(user=first_user)
        second_profile = StudentProfile.objects.create(user=second_user)
        first_interest = Interest.objects.create(name="First private interest", slug="private-one")
        second_interest = Interest.objects.create(name="Second private interest", slug="private-two")
        StudentInterest.objects.create(student_profile=first_profile, interest=first_interest)
        StudentInterest.objects.create(student_profile=second_profile, interest=second_interest)

        first_client = APIClient()
        first_client.force_authenticate(first_user)
        second_client = APIClient()
        second_client.force_authenticate(second_user)

        first = first_client.get("/api/education/student-interests/")
        second = second_client.get("/api/education/student-interests/")

        self.assertEqual([item["interest"] for item in first.data["results"]], [first_interest.pk])
        self.assertEqual([item["interest"] for item in second.data["results"]], [second_interest.pk])
