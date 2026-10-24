"""Temporary, fail-closed Subjects API measurement harness.

This file is intentionally untracked. Run it only through Django's test runner
from the backend directory, then remove it with the cleanup command provided in
the task handoff.
"""

from __future__ import annotations

import os
import statistics
from collections import Counter
from time import perf_counter


EXPECTED_SOURCE = {
    "ENGINE": "django.db.backends.postgresql",
    "HOST": "127.0.0.1",
    "PORT": "5432",
    "NAME": "studymate_test",
    "USER": "studymate_test_user",
}
EXPECTED_TEST_NAME = "test_studymate_test"


if not os.environ.get("DATABASE_URL", "").strip():
    raise RuntimeError("BLOCKED: DATABASE_URL must be set in the process environment.")


from django.conf import settings
from django.contrib.auth.models import User
from django.db import connection, connections
from django.test import TestCase
from django.test.runner import DiscoverRunner
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient

from apps.community.models import DiscussionComment, DiscussionCommentLike
from apps.education.models import AcademicLevel, Course, EducationBackground, Interest, StudentInterest
from apps.interactions.models import ResourceRating, ResourceUpvote, SavedResource
from apps.resources.models import PublicationStatus, Resource, ResourceDownload, ResourceView, Video
from apps.users.models import StudentProfile


def _assert_local_test_target() -> None:
    """Validate settings before Django creates or connects to a test database."""

    database = connections["default"]
    resolved = database.settings_dict
    actual = {
        "ENGINE": str(resolved.get("ENGINE", "")),
        "HOST": str(resolved.get("HOST", "")),
        "PORT": str(resolved.get("PORT", "")),
        "NAME": str(resolved.get("NAME", "")),
        "USER": str(resolved.get("USER", "")),
    }
    derived_test_name = database.creation._get_test_db_name()

    if actual != EXPECTED_SOURCE:
        raise RuntimeError(
            "BLOCKED: Django database target is not the required loopback target. "
            "No test database was created."
        )
    if derived_test_name != EXPECTED_TEST_NAME:
        raise RuntimeError(
            "BLOCKED: Django did not derive the required isolated test database. "
            "No test database was created."
        )


class LocalOnlyDiscoverRunner(DiscoverRunner):
    """Reject every target except the verified local source and test database."""

    def setup_databases(self, **kwargs):
        _assert_local_test_target()
        return super().setup_databases(**kwargs)


def _p95(values: list[float]) -> float:
    return statistics.quantiles(values, n=100, method="inclusive")[94]


class SubjectRecommendationMeasurement(TestCase):
    """Measure only the authenticated Subjects API request."""

    @classmethod
    def setUpTestData(cls) -> None:
        cls.user = User.objects.create_user(
            username="phase1-measurement-user",
        )
        cls.peer = User.objects.create_user(
            username="phase1-measurement-peer",
        )
        background = EducationBackground.objects.create(
            name="Measurement Engineering",
            slug="phase1-measurement-engineering",
        )
        course = Course.objects.create(
            education_background=background,
            name="Measurement Course",
            slug="phase1-measurement-course",
        )
        level = AcademicLevel.objects.create(
            course=course,
            name="Measurement Level",
            slug="phase1-measurement-level",
            level_type=AcademicLevel.LevelType.SEMESTER,
            order=1,
        )
        profile = StudentProfile.objects.create(
            user=cls.user,
            education_background=background,
            course=course,
            academic_level=level,
            onboarding_completed=True,
        )
        interest = Interest.objects.create(
            name="Measurement Subject 1",
            slug="phase1-measurement-subject-1",
        )
        interest.courses.add(course)
        StudentInterest.objects.create(student_profile=profile, interest=interest)

        for index in range(5):
            subject = f"Measurement Subject {index + 1}"
            resource = Resource.objects.create(
                title=f"{subject} resource",
                description="Representative measurement fixture.",
                uploader=cls.user,
                subject=subject,
                topic="Measurement topic",
                course="Measurement Course",
                semester="1",
                academic_level=level,
                resource_type=Resource.ResourceType.NOTES,
                status=PublicationStatus.PUBLISHED,
            )
            Video.objects.create(
                title=f"{subject} video",
                description="Representative measurement fixture.",
                uploader=cls.peer,
                subject=subject,
                topic="Measurement topic",
                course="Measurement Course",
                semester="1",
                academic_level=level,
                youtube_video_id=f"MEAS{index:07d}",
                status=PublicationStatus.PUBLISHED,
            )

            if index == 0:
                ResourceView.objects.create(resource=resource, user=cls.peer)
                ResourceDownload.objects.create(resource=resource, user=cls.peer)
                SavedResource.objects.create(resource=resource, user=cls.peer)
                ResourceUpvote.objects.create(resource=resource, user=cls.peer)
                ResourceRating.objects.create(resource=resource, user=cls.peer, rating=5)
                comment = DiscussionComment.objects.create(
                    resource=resource,
                    author=cls.peer,
                    body="Representative measurement comment.",
                    status=PublicationStatus.PUBLISHED,
                )
                DiscussionCommentLike.objects.create(comment=comment, user=cls.user)

    def setUp(self) -> None:
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_subjects_measurement(self) -> None:
        for _ in range(3):
            response = self.client.get("/api/resources/subjects/")
            self.assertEqual(response.status_code, 200)

        latency_ms: list[float] = []
        query_counts: list[int] = []
        response_sizes: list[int] = []
        statuses: list[int] = []

        for _ in range(20):
            with CaptureQueriesContext(connection) as queries:
                started = perf_counter()
                response = self.client.get("/api/resources/subjects/")
                response_size = len(response.content)
                elapsed = (perf_counter() - started) * 1000

            latency_ms.append(elapsed)
            query_counts.append(len(queries))
            response_sizes.append(response_size)
            statuses.append(response.status_code)

        status_counts = ",".join(
            f"{status}={count}" for status, count in sorted(Counter(statuses).items())
        )
        print("SUBJECTS_MEASUREMENT")
        print("warmups=3 samples=20")
        print(f"http_status_counts={status_counts}")
        print(f"latency_ms_median={statistics.median(latency_ms):.3f}")
        print(f"latency_ms_p95={_p95(latency_ms):.3f}")
        print(
            "query_count_min="
            f"{min(query_counts)} query_count_median={statistics.median(query_counts):.1f} "
            f"query_count_max={max(query_counts)}"
        )
        print(f"response_bytes_median={statistics.median(response_sizes):.1f}")
        print(f"response_bytes_p95={_p95([float(size) for size in response_sizes]):.1f}")

        self.assertTrue(all(status == 200 for status in statuses))
