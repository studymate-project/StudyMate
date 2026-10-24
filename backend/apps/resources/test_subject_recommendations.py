import threading
import time
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

from django.core.cache import cache
from django.contrib.auth.models import User
from django.db import transaction
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.community.models import DiscussionComment, DiscussionCommentLike
from apps.education.models import AcademicLevel, Course, EducationBackground, Interest, StudentInterest
from apps.interactions.models import ResourceRating, ResourceUpvote, SavedResource
from apps.users.models import StudentProfile
from apps.resources import views as resource_views
from apps.resources.subject_cache import (
    get_subject_cache_version,
    get_subject_user_cache_version,
)
from apps.users.serializers import StudentProfileSerializer

from .models import PublicationStatus, Resource, ResourceDownload, ResourceView


@override_settings(
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "subject-recommendation-tests",
        }
    }
)
class SubjectRecommendationAPITests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username="subject-student", password="not-used-in-test")
        cls.peer = User.objects.create_user(username="subject-peer", password="not-used-in-test")
        cls.engineering = EducationBackground.objects.create(name="Engineering", slug="test-engineering")
        cls.commerce = EducationBackground.objects.create(name="Commerce", slug="test-commerce")
        cls.btech = Course.objects.create(education_background=cls.engineering, name="B.Tech CSE", slug="test-btech-cse")
        cls.bcom = Course.objects.create(education_background=cls.commerce, name="B.Com", slug="test-bcom")
        cls.btech_level = AcademicLevel.objects.create(
            course=cls.btech,
            name="1st Semester",
            slug="test-btech-semester-1",
            level_type=AcademicLevel.LevelType.SEMESTER,
            order=1,
        )
        cls.bcom_level = AcademicLevel.objects.create(
            course=cls.bcom,
            name="1st Year",
            slug="test-bcom-year-1",
            level_type=AcademicLevel.LevelType.YEAR,
            order=1,
        )

    def setUp(self):
        self.client = APIClient()
        cache.clear()
        self.client.force_authenticate(self.user)
        self.profile = StudentProfile.objects.create(
            user=self.user,
            education_background=self.engineering,
            course=self.btech,
            academic_level=self.btech_level,
            onboarding_completed=True,
        )

    def create_resource(self, subject, *, academic_level=None):
        return Resource.objects.create(
            title=f"{subject} notes",
            uploader=self.user,
            subject=subject,
            academic_level=academic_level,
            resource_type=Resource.ResourceType.NOTES,
            status=PublicationStatus.PUBLISHED,
        )

    def test_recommendations_combine_academic_interest_and_real_engagement(self):
        data_structures = self.create_resource("Data Structures", academic_level=self.btech_level)
        self.create_resource("AI/ML", academic_level=self.btech_level)
        ai_interest = Interest.objects.create(name="AI/ML", slug="test-ai-ml")
        ai_interest.courses.add(self.btech)
        StudentInterest.objects.create(student_profile=self.profile, interest=ai_interest)

        ResourceView.objects.create(resource=data_structures, user=self.peer)
        ResourceDownload.objects.create(resource=data_structures, user=self.peer)
        SavedResource.objects.create(resource=data_structures, user=self.peer)
        ResourceUpvote.objects.create(resource=data_structures, user=self.peer)
        ResourceRating.objects.create(resource=data_structures, user=self.peer, rating=5)
        comment = DiscussionComment.objects.create(resource=data_structures, author=self.peer, body="Helpful")
        DiscussionCommentLike.objects.create(comment=comment, user=self.user)

        response = self.client.get("/api/resources/subjects/")

        self.assertEqual(response.status_code, 200)
        subjects = response.data["results"]
        by_name = {subject["name"]: subject for subject in subjects}
        self.assertIn("Data Structures", by_name)
        self.assertIn("AI/ML", by_name)
        self.assertGreaterEqual(by_name["Data Structures"]["engagement_count"], 7)
        self.assertTrue(by_name["Data Structures"]["is_trending"])
        self.assertTrue(by_name["AI/ML"]["is_personalized"])

    def test_course_change_prioritizes_the_new_course_without_fixed_mappings(self):
        accounting_interest = Interest.objects.create(name="Accounting", slug="test-accounting")
        accounting_interest.courses.add(self.bcom)
        StudentInterest.objects.create(student_profile=self.profile, interest=accounting_interest)
        self.profile.education_background = self.commerce
        self.profile.course = self.bcom
        self.profile.academic_level = self.bcom_level
        self.profile.save(update_fields=["education_background", "course", "academic_level"])
        self.create_resource("Accounting", academic_level=self.bcom_level)

        response = self.client.get("/api/resources/subjects/")

        self.assertEqual(response.status_code, 200)
        accounting = next(subject for subject in response.data["results"] if subject["name"] == "Accounting")
        self.assertTrue(accounting["is_personalized"])

    def test_incomplete_profile_uses_general_subjects_and_zero_engagement_is_safe(self):
        self.profile.onboarding_completed = False
        self.profile.save(update_fields=["onboarding_completed"])
        new_subject = self.create_resource("General Mathematics")
        course_interest = Interest.objects.create(name="Study Skills", slug="test-study-skills")
        course_interest.courses.add(self.btech)

        response = self.client.get("/api/resources/subjects/")

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["profile_complete"])
        subjects = {subject["name"]: subject for subject in response.data["results"]}
        self.assertIn("General Mathematics", subjects)
        self.assertGreaterEqual(subjects["General Mathematics"]["content_count"], 1)
        self.assertEqual(subjects["General Mathematics"]["engagement_count"], 0)
        self.assertNotIn("Study Skills", subjects)
        self.assertNotEqual(new_subject.subject, "")

    def test_endpoint_requires_authentication(self):
        self.client.force_authenticate(user=None)

        response = self.client.get("/api/resources/subjects/")

        self.assertEqual(response.status_code, 401)

    def test_cache_miss_populates_global_and_user_entries_and_hit_skips_aggregate_queries(self):
        self.create_resource("Data Structures", academic_level=self.btech_level)

        with patch(
            "apps.resources.views._resource_subject_stats",
            wraps=resource_views._resource_subject_stats,
        ) as resource_stats, patch(
            "apps.resources.views._calculate_subject_recommendations",
            wraps=resource_views._calculate_subject_recommendations,
        ) as calculate_recommendations:
            first = self.client.get("/api/resources/subjects/")
            second = self.client.get("/api/resources/subjects/")

        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.data, second.data)
        self.assertEqual(resource_stats.call_count, 1)
        self.assertEqual(calculate_recommendations.call_count, 1)
        self.assertIsNotNone(cache.get(resource_views._subject_global_cache_key()))
        self.assertIsNotNone(
            cache.get(
                resource_views._subject_user_cache_key(
                    self.user,
                    self.profile,
                    12,
                )
            )
        )

    def test_different_users_use_separate_personalized_cache_entries(self):
        self.create_resource("Data Structures", academic_level=self.btech_level)
        engineering_interest = Interest.objects.create(name="Data Structures", slug="test-data-structures")
        engineering_interest.courses.add(self.btech)
        StudentInterest.objects.create(student_profile=self.profile, interest=engineering_interest)

        other = User.objects.create_user(username="subject-other", password="not-used-in-test")
        other_profile = StudentProfile.objects.create(
            user=other,
            education_background=self.commerce,
            course=self.bcom,
            academic_level=self.bcom_level,
            onboarding_completed=True,
        )
        commerce_interest = Interest.objects.create(name="Accounting", slug="test-accounting")
        commerce_interest.courses.add(self.bcom)
        StudentInterest.objects.create(student_profile=other_profile, interest=commerce_interest)

        first = self.client.get("/api/resources/subjects/")
        other_client = APIClient()
        other_client.force_authenticate(other)
        second = other_client.get("/api/resources/subjects/")

        first_subjects = {item["name"]: item for item in first.data["results"]}
        second_subjects = {item["name"]: item for item in second.data["results"]}
        self.assertTrue(first_subjects["Data Structures"]["is_personalized"])
        self.assertTrue(second_subjects["Accounting"]["is_personalized"])

    def test_different_limits_use_separate_cache_entries(self):
        self.create_resource("Data Structures")
        self.create_resource("Operating Systems")

        one = self.client.get("/api/resources/subjects/?limit=1")
        two = self.client.get("/api/resources/subjects/?limit=2")

        self.assertEqual(one.status_code, 200)
        self.assertEqual(two.status_code, 200)
        self.assertEqual(one.data["count"], 1)
        self.assertEqual(two.data["count"], 2)

    @override_settings(
        SUBJECT_RECOMMENDATION_CACHE_TTL_SECONDS=1,
        SUBJECT_RECOMMENDATION_CACHE_TTL_JITTER_SECONDS=0,
    )
    def test_expired_cache_recomputes(self):
        self.create_resource("Data Structures")
        self.client.get("/api/resources/subjects/")
        time.sleep(1.1)

        with patch(
            "apps.resources.views._resource_subject_stats",
            wraps=resource_views._resource_subject_stats,
        ) as resource_stats:
            response = self.client.get("/api/resources/subjects/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(resource_stats.call_count, 1)

    def test_cache_failures_fall_back_to_database_logic(self):
        self.create_resource("Data Structures")

        real_get = cache.get
        real_set = cache.set

        def failing_get(key, *args, **kwargs):
            if str(key).startswith("studymate:subjects:"):
                raise RuntimeError("cache unavailable")
            return real_get(key, *args, **kwargs)

        def failing_set(key, *args, **kwargs):
            if str(key).startswith("studymate:subjects:"):
                raise RuntimeError("cache unavailable")
            return real_set(key, *args, **kwargs)

        with patch("apps.resources.views.cache.get", side_effect=failing_get), patch(
            "apps.resources.views.cache.set", side_effect=failing_set
        ):
            response = self.client.get("/api/resources/subjects/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Data Structures", {item["name"] for item in response.data["results"]})

    def test_committed_published_resource_invalidates_subject_cache(self):
        self.client.get("/api/resources/subjects/")
        previous_version = get_subject_cache_version()

        with self.captureOnCommitCallbacks(execute=True):
            with transaction.atomic():
                self.create_resource("Committed Subject")

        self.assertNotEqual(get_subject_cache_version(), previous_version)
        response = self.client.get("/api/resources/subjects/")

        self.assertIn("Committed Subject", {item["name"] for item in response.data["results"]})

    def test_published_subject_update_invalidates_subject_cache(self):
        resource = self.create_resource("Old Subject")
        self.client.get("/api/resources/subjects/")

        with self.captureOnCommitCallbacks(execute=True):
            with transaction.atomic():
                resource.subject = "New Subject"
                resource.save(update_fields=["subject"])

        response = self.client.get("/api/resources/subjects/")
        names = {item["name"] for item in response.data["results"]}
        self.assertIn("New Subject", names)
        self.assertNotIn("Old Subject", names)

    def test_published_resource_delete_invalidates_subject_cache(self):
        resource = self.create_resource("Deleted Subject")
        self.client.get("/api/resources/subjects/")

        with self.captureOnCommitCallbacks(execute=True):
            with transaction.atomic():
                resource.delete()

        response = self.client.get("/api/resources/subjects/")
        self.assertNotIn("Deleted Subject", {item["name"] for item in response.data["results"]})

    def test_rolled_back_resource_does_not_invalidate_or_appear_in_subject_cache(self):
        self.client.get("/api/resources/subjects/")
        previous_version = get_subject_cache_version()

        with self.captureOnCommitCallbacks(execute=True):
            try:
                with transaction.atomic():
                    self.create_resource("Rolled Back Subject")
                    raise RuntimeError("rollback test")
            except RuntimeError:
                pass

        self.assertEqual(get_subject_cache_version(), previous_version)
        response = self.client.get("/api/resources/subjects/")

        self.assertNotIn("Rolled Back Subject", {item["name"] for item in response.data["results"]})

    def test_view_and_download_history_remain_durable_without_per_event_cache_writes(self):
        resource = self.create_resource("Engaged Subject")
        first = self.client.get("/api/resources/subjects/")
        first_subject = next(item for item in first.data["results"] if item["name"] == "Engaged Subject")
        self.assertEqual(first_subject["engagement_count"], 0)
        previous_version = get_subject_cache_version()

        with self.captureOnCommitCallbacks(execute=True):
            with transaction.atomic():
                ResourceView.objects.create(resource=resource, user=self.peer)
                ResourceDownload.objects.create(resource=resource, user=self.peer)

        self.assertEqual(get_subject_cache_version(), previous_version)
        self.assertEqual(ResourceView.objects.filter(resource=resource).count(), 1)
        self.assertEqual(ResourceDownload.objects.filter(resource=resource).count(), 1)

        cache.clear()
        response = self.client.get("/api/resources/subjects/")
        subject = next(item for item in response.data["results"] if item["name"] == "Engaged Subject")
        self.assertEqual(subject["engagement_count"], 2)

    def test_repeated_telemetry_posts_preserve_each_event_row(self):
        resource = self.create_resource("Repeated Events")

        ResourceView.objects.create(resource=resource, user=self.peer)
        ResourceView.objects.create(resource=resource, user=self.peer)
        ResourceDownload.objects.create(resource=resource, user=self.peer)
        ResourceDownload.objects.create(resource=resource, user=self.peer)

        self.assertEqual(ResourceView.objects.filter(resource=resource).count(), 2)
        self.assertEqual(ResourceDownload.objects.filter(resource=resource).count(), 2)

    def test_bulk_interest_update_invalidates_only_after_commit(self):
        resource = self.create_resource("Interest Subject", academic_level=self.bcom_level)
        interest = Interest.objects.create(name="Interest Subject", slug="test-interest-subject")
        interest.courses.add(self.btech)
        self.client.get("/api/resources/subjects/")
        previous_version = get_subject_user_cache_version(self.user.pk)

        serializer = StudentProfileSerializer(
            self.profile,
            data={"interest_ids": [interest.pk]},
            partial=True,
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        with self.captureOnCommitCallbacks(execute=True):
            with transaction.atomic():
                serializer.save()

        response = self.client.get("/api/resources/subjects/")
        subject = next(item for item in response.data["results"] if item["name"] == "Interest Subject")
        self.assertTrue(subject["is_personalized"])
        self.assertNotEqual(get_subject_user_cache_version(self.user.pk), previous_version)

    def test_cache_invalidation_failure_does_not_break_committed_write(self):
        with patch(
            "apps.resources.subject_cache.cache.set",
            side_effect=RuntimeError("cache unavailable"),
        ):
            with self.captureOnCommitCallbacks(execute=True):
                with transaction.atomic():
                    resource = self.create_resource("Cache Failure Subject")

        self.assertTrue(Resource.objects.filter(pk=resource.pk).exists())

    def test_concurrent_cache_misses_rebuild_aggregate_once(self):
        class FakeLock:
            def __init__(self, backend, kwargs):
                self.backend = backend
                self.kwargs = kwargs
                self.acquired = False
                self.release_calls = 0

            def acquire(self):
                if self.backend.mutex.locked():
                    self.backend.contention_seen.set()
                acquired = self.backend.mutex.acquire(timeout=self.kwargs["blocking_timeout"])
                self.acquired = acquired
                return acquired

            def release(self):
                if not self.acquired:
                    raise AssertionError("a lock owner must be required to release")
                self.release_calls += 1
                self.backend.mutex.release()

        class FakeCache:
            def __init__(self):
                self.values = {}
                self.mutex = threading.Lock()
                self.contention_seen = threading.Event()
                self.lock_kwargs = []

            def get(self, key):
                return self.values.get(key)

            def set(self, key, value, **kwargs):
                self.values[key] = value

            def lock(self, key, **kwargs):
                self.lock_kwargs.append((key, kwargs))
                return FakeLock(self, kwargs)

        fake_cache = FakeCache()
        aggregate_started = threading.Event()
        allow_aggregate = threading.Event()
        aggregate_calls = 0
        aggregate_calls_lock = threading.Lock()

        def resource_stats(_cutoff):
            nonlocal aggregate_calls
            with aggregate_calls_lock:
                aggregate_calls += 1
            aggregate_started.set()
            self.assertTrue(allow_aggregate.wait(2))
            return []

        with patch("apps.resources.views.cache", fake_cache), patch(
            "apps.resources.views._subject_global_cache_key",
            return_value="studymate:subjects:test-global",
        ), patch(
            "apps.resources.views._resource_subject_stats",
            side_effect=resource_stats,
        ), patch("apps.resources.views._video_subject_stats", return_value=[]):
            with ThreadPoolExecutor(max_workers=2) as executor:
                first = executor.submit(resource_views._cached_subject_stats)
                self.assertTrue(aggregate_started.wait(2))
                second = executor.submit(resource_views._cached_subject_stats)
                self.assertTrue(fake_cache.contention_seen.wait(2))
                allow_aggregate.set()
                first_result = first.result(timeout=2)
                second_result = second.result(timeout=2)

        self.assertEqual(aggregate_calls, 1)
        self.assertEqual(first_result, second_result)
        self.assertEqual(len(fake_cache.lock_kwargs), 2)

    def test_lock_contention_falls_back_after_bounded_wait_without_release(self):
        class ContendedLock:
            def __init__(self, kwargs):
                self.kwargs = kwargs
                self.release_calls = 0

            def acquire(self):
                return False

            def release(self):
                self.release_calls += 1
                raise AssertionError("a non-owner lock must not be released")

        class ContendedCache:
            def __init__(self):
                self.lock_instance = None

            def get(self, _key):
                return None

            def set(self, _key, _value, **_kwargs):
                return None

            def lock(self, _key, **kwargs):
                self.lock_instance = ContendedLock(kwargs)
                return self.lock_instance

        fake_cache = ContendedCache()
        with patch("apps.resources.views.cache", fake_cache), patch(
            "apps.resources.views._subject_global_cache_key",
            return_value="studymate:subjects:test-contention",
        ), patch(
            "apps.resources.views._resource_subject_stats",
            return_value=[],
        ), patch("apps.resources.views._video_subject_stats", return_value=[]):
            result = resource_views._cached_subject_stats()

        self.assertEqual(result, {})
        self.assertEqual(fake_cache.lock_instance.release_calls, 0)
        self.assertGreater(fake_cache.lock_instance.kwargs["timeout"], 0)
        self.assertEqual(
            fake_cache.lock_instance.kwargs["timeout"],
            resource_views.SUBJECT_CACHE_LOCK_TIMEOUT_SECONDS,
        )
        self.assertGreater(fake_cache.lock_instance.kwargs["blocking_timeout"], 0)
        self.assertLessEqual(
            fake_cache.lock_instance.kwargs["blocking_timeout"],
            resource_views.SUBJECT_CACHE_LOCK_WAIT_SECONDS,
        )

    def test_lock_failure_falls_back_to_database_and_does_not_cache_errors(self):
        class BrokenCache:
            def get(self, _key):
                return None

            def set(self, _key, _value, **_kwargs):
                raise AssertionError("the fallback must not cache through a broken cache")

            def lock(self, _key, **_kwargs):
                raise RuntimeError("redis unavailable")

        with patch("apps.resources.views.cache", BrokenCache()), patch(
            "apps.resources.views._subject_global_cache_key",
            return_value="studymate:subjects:test-lock-failure",
        ), patch(
            "apps.resources.views._resource_subject_stats",
            return_value=[],
        ), patch("apps.resources.views._video_subject_stats", return_value=[]):
            self.assertEqual(resource_views._cached_subject_stats(), {})

    def test_owned_lock_releases_when_database_rebuild_fails(self):
        class OwnerLock:
            def __init__(self, kwargs):
                self.kwargs = kwargs
                self.release_calls = 0

            def acquire(self):
                return True

            def release(self):
                self.release_calls += 1

        class CacheWithOwnedLock:
            def __init__(self):
                self.lock_instance = None

            def get(self, _key):
                return None

            def lock(self, _key, **kwargs):
                self.lock_instance = OwnerLock(kwargs)
                return self.lock_instance

            def set(self, _key, _value, **_kwargs):
                raise AssertionError("an incomplete aggregate must not be cached")

        fake_cache = CacheWithOwnedLock()
        with patch("apps.resources.views.cache", fake_cache), patch(
            "apps.resources.views._subject_global_cache_key",
            return_value="studymate:subjects:test-rebuild-error",
        ), patch(
            "apps.resources.views._resource_subject_stats",
            side_effect=RuntimeError("database unavailable"),
        ), self.assertRaises(RuntimeError):
            resource_views._cached_subject_stats()

        self.assertEqual(fake_cache.lock_instance.release_calls, 1)
