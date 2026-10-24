"""Temporary, fail-closed unified-search measurement harness.

This file is intentionally untracked. Run it only through Django's test runner
from the repository root with the explicit command in the task handoff. It
must use the local PostgreSQL source database ``studymate_test`` so Django can
create and use only ``test_studymate_test``.
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


from django.contrib.auth.models import User
from django.conf import settings
from django.db import connection, connections
from django.test import TestCase
from django.test.runner import DiscoverRunner
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient

from apps.community.models import Question
from apps.resources.models import PublicationStatus, Resource, Tag, Video
from apps.users.models import StudentProfile


def _assert_local_test_target() -> None:
    """Validate Django settings before creating or connecting to a test DB."""

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


def _print_metrics(label: str, latencies: list[float], query_counts: list[int], statuses: list[int], sizes: list[int]) -> None:
    status_counts = ",".join(
        f"{status}={count}" for status, count in sorted(Counter(statuses).items())
    )
    print(f"SEARCH_MEASUREMENT case={label}")
    print("warmups=3 samples=20")
    print(f"http_status_counts={status_counts}")
    print(f"latency_ms_median={statistics.median(latencies):.3f}")
    print(f"latency_ms_p95={_p95(latencies):.3f}")
    print(
        "query_count_min="
        f"{min(query_counts)} query_count_median={statistics.median(query_counts):.1f} "
        f"query_count_max={max(query_counts)}"
    )
    print(f"response_bytes_median={statistics.median(sizes):.1f}")
    print(f"response_bytes_p95={_p95([float(size) for size in sizes]):.1f}")


class UnifiedSearchMeasurement(TestCase):
    """Measure only the public unified search endpoint."""

    @classmethod
    def setUpTestData(cls) -> None:
        cls.user = User.objects.create_user(
            username="phase1-search-user",
            first_name="Python",
            last_name="Learner",
        )
        StudentProfile.objects.create(
            user=cls.user,
            display_name="Python Learner",
            bio="Studies Python algorithms and data structures.",
        )
        uploader = User.objects.create_user(username="phase1-search-uploader")
        tag = Tag.objects.create(name="Python", slug="python")

        for index in range(5):
            resource = Resource.objects.create(
                title=f"Python algorithms notes {index}",
                description="Representative search resource for Python data structures.",
                uploader=uploader,
                subject="Computer Science",
                topic="Algorithms",
                course="Measurement Course",
                semester="1",
                resource_type=Resource.ResourceType.NOTES,
                status=PublicationStatus.PUBLISHED,
            )
            resource.tags.add(tag)
            Video.objects.create(
                title=f"Python algorithms lecture {index}",
                description="Representative search video for Python algorithms.",
                uploader=uploader,
                youtube_video_id=f"SRCH{index:07d}",
                subject="Computer Science",
                topic="Algorithms",
                course="Measurement Course",
                semester="1",
                status=PublicationStatus.PUBLISHED,
            )
            Question.objects.create(
                title=f"How does Python algorithm {index} work?",
                body="A representative question about Python data structures.",
                author=uploader,
                subject="Computer Science",
                topic="Algorithms",
                status=PublicationStatus.PUBLISHED,
            )

    def setUp(self) -> None:
        self.client = APIClient()

    def _measure_case(self, label: str, params: dict[str, str], expected_status: int) -> None:
        for _ in range(3):
            response = self.client.get("/api/search/", params)
            self.assertEqual(response.status_code, expected_status)

        latencies: list[float] = []
        query_counts: list[int] = []
        statuses: list[int] = []
        response_sizes: list[int] = []

        for _ in range(20):
            with CaptureQueriesContext(connection) as queries:
                started = perf_counter()
                response = self.client.get("/api/search/", params)
                response_size = len(response.content)
                elapsed = (perf_counter() - started) * 1000

            latencies.append(elapsed)
            query_counts.append(len(queries))
            statuses.append(response.status_code)
            response_sizes.append(response_size)

        _print_metrics(label, latencies, query_counts, statuses, response_sizes)
        self.assertTrue(all(status == expected_status for status in statuses))

    def test_unified_search_measurement(self) -> None:
        self._measure_case("q=python", {"q": "python"}, 200)
        self._measure_case("q=python_limit=5_offset=0", {"q": "python", "limit": "5", "offset": "0"}, 200)
        self._measure_case("missing-q", {}, 400)
