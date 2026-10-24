"""Temporary, fail-closed PostgreSQL plan inspection harness for /api/search/.

This file is intentionally untracked. Run it only through Django's test runner
with the explicit PowerShell command in the task handoff. It creates bounded
fixtures in Django's derived test database and prints plan metadata only; SQL,
parameters, credentials, and fixture values are never printed.
"""

from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from urllib.parse import urlsplit


REPOSITORY_ROOT = Path(__file__).resolve().parent
BACKEND_ROOT = REPOSITORY_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")


EXPECTED_SOURCE = {
    "ENGINE": "django.db.backends.postgresql",
    "HOST": "127.0.0.1",
    "PORT": "5432",
    "NAME": "studymate_test",
    "USER": "studymate_test_user",
}
EXPECTED_TEST_NAME = "test_studymate_test"
CONTENT_ROWS = 1000
PUBLIC_USER_ROWS = 300
TAG_EVERY = 4
MATCH_EVERY = 10


def _assert_process_database_url() -> None:
    raw_url = os.environ.get("DATABASE_URL", "").strip()
    if not raw_url:
        raise RuntimeError("BLOCKED: DATABASE_URL must be set in the process environment.")

    try:
        parsed = urlsplit(raw_url)
        actual = {
            "ENGINE": "django.db.backends.postgresql",
            "HOST": parsed.hostname or "",
            "PORT": str(parsed.port or 5432),
            "NAME": parsed.path.lstrip("/"),
            "USER": parsed.username or "",
        }
    except (TypeError, ValueError):
        raise RuntimeError("BLOCKED: DATABASE_URL is not a valid local PostgreSQL URL.")

    if actual != EXPECTED_SOURCE:
        raise RuntimeError("BLOCKED: DATABASE_URL is not the required loopback test source.")


def _assert_safe_invocation() -> None:
    blocked = ("--keepdb", "--parallel", "--database")
    for argument in sys.argv[1:]:
        if argument in blocked or any(argument.startswith(f"{item}=") for item in blocked):
            raise RuntimeError("BLOCKED: unsafe Django test-runner option was supplied.")


_assert_process_database_url()
_assert_safe_invocation()


from django.contrib.auth.models import User
from django.db import connection, connections
from django.test import SimpleTestCase, TestCase
from django.test.runner import DiscoverRunner
from django.utils import timezone
from rest_framework.test import APIClient

from apps.community.models import Question
from apps.resources.models import PublicationStatus, Resource, Tag, Video
from apps.users.models import StudentProfile


def _assert_django_database_target() -> None:
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
        raise RuntimeError("BLOCKED: Django resolved an unsafe database source target.")
    if derived_test_name != EXPECTED_TEST_NAME:
        raise RuntimeError("BLOCKED: Django did not derive test_studymate_test.")


class LocalOnlyDiscoverRunner(DiscoverRunner):
    """Refuse test-database setup unless the local source is verified first."""

    def setup_databases(self, **kwargs):
        _assert_django_database_target()
        return super().setup_databases(**kwargs)


class _SelectCapture:
    """Capture search SELECT SQL and parameters without displaying either."""

    def __init__(self) -> None:
        self.statements: list[tuple[str, object]] = []

    def __call__(self, execute, sql, params, many, context):
        normalized = sql.lstrip().lower()
        if normalized.startswith("select") and "set_config" not in normalized:
            self.statements.append((sql, params))
        return execute(sql, params, many, context)


BRANCH_TABLES = (
    ("resource", "resources_resource"),
    ("video", "resources_video"),
    ("question", "community_question"),
    ("public-user", "auth_user"),
)

EXPECTED_SEARCH_INDEXES = (
    ("resource", "resources_resource", "resources_resource_search_fts"),
    ("resource", "resources_resource", "resources_resource_search_trgm"),
    ("video", "resources_video", "resources_video_search_fts"),
    ("video", "resources_video", "resources_video_search_trgm"),
    ("question", "community_question", "community_question_search_fts"),
    ("question", "community_question", "community_question_search_trgm"),
)

PLAN_PREDICATE_FIELDS = (
    "Filter",
    "Index Cond",
    "Recheck Cond",
    "Join Filter",
    "Hash Cond",
    "Merge Cond",
)
FTS_PREDICATE_RE = re.compile(r"\bsearch_vector\b\s*@@", re.IGNORECASE)
TRIGRAM_OPERATOR_RE = re.compile(r"(?<!\S)%(?!\S)")


@dataclass(frozen=True)
class _PredicateSummary:
    """Predicates detected from SQL and explicit PostgreSQL predicate fields."""

    full_text: bool
    trigram: bool
    full_text_source: str
    trigram_source: str


def _plan_predicate_text(node: dict) -> str:
    """Return only plan fields that can contain a predicate expression."""

    expressions = [
        str(node[field])
        for field in PLAN_PREDICATE_FIELDS
        if node.get(field) is not None
    ]
    for child in node.get("Plans", []):
        child_text = _plan_predicate_text(child)
        if child_text:
            expressions.append(child_text)
    return "\n".join(expressions)


def _predicate_source(sql_match: bool, plan_match: bool) -> str:
    if sql_match and plan_match:
        return "sql+plan"
    if sql_match:
        return "sql"
    if plan_match:
        return "plan"
    return "none"


def _predicate_summary(sql: str, plan: dict | None = None) -> _PredicateSummary:
    """Detect operators from SQL and named plan predicate fields only.

    PostgreSQL's JSON plan can contain the useful predicate in ``Filter`` or
    ``Recheck Cond`` even when the captured driver SQL is not rendered with the
    same expression text. Do not stringify the entire plan: that can produce
    false matches from unrelated metadata or redacted values.
    """

    plan_text = _plan_predicate_text(plan) if plan else ""
    full_text_sql = bool(FTS_PREDICATE_RE.search(sql))
    full_text_plan = bool(FTS_PREDICATE_RE.search(plan_text))
    trigram_sql = bool(TRIGRAM_OPERATOR_RE.search(sql))
    trigram_plan = bool(TRIGRAM_OPERATOR_RE.search(plan_text))

    return _PredicateSummary(
        full_text=full_text_sql or full_text_plan,
        trigram=trigram_sql or trigram_plan,
        full_text_source=_predicate_source(full_text_sql, full_text_plan),
        trigram_source=_predicate_source(trigram_sql, trigram_plan),
    )


def _branch_for_sql(sql: str) -> str | None:
    normalized = sql.lower()
    for branch, table_name in BRANCH_TABLES:
        if table_name in normalized:
            return branch
    return None


def _plan_document(cursor, sql: str, params):
    cursor.execute("EXPLAIN (FORMAT JSON) " + sql, params)
    document = cursor.fetchone()[0]
    return json.loads(document) if isinstance(document, str) else document


def _redact_plan_expression(value: object) -> str:
    if value is None:
        return ""
    expression = str(value)
    return re.sub(r"'(?:''|[^'])*'", "'<redacted>'", expression)


def _plan_scan_details(node: dict) -> tuple[str, str]:
    node_type = str(node.get("Node Type", ""))
    if "Scan" not in node_type:
        return "", ""
    return node_type, str(node.get("Index Name") or "")


def _collect_index_usage(node: dict, scans: list[tuple[str, str]]) -> None:
    scan_type, index_name = _plan_scan_details(node)
    if scan_type:
        scans.append((scan_type, index_name))
    for child in node.get("Plans", []):
        _collect_index_usage(child, scans)


def _print_plan_nodes(case: str, branch: str, node: dict) -> None:
    scan_type, index_name = _plan_scan_details(node)
    print(
        f"case={case} branch={branch} node={node.get('Node Type', '')} "
        f"relation={node.get('Relation Name', '')} "
        f"scan_type={scan_type or '-'} "
        f"index_name={index_name or '-'} "
        f"index_used={'yes' if index_name else 'no'} "
        f"estimated_rows={node.get('Plan Rows', '')} "
        f"startup_cost={node.get('Startup Cost', '')} "
        f"total_cost={node.get('Total Cost', '')} "
        f"filter={_redact_plan_expression(node.get('Filter'))} "
        f"index_cond={_redact_plan_expression(node.get('Index Cond'))} "
        f"recheck_cond={_redact_plan_expression(node.get('Recheck Cond'))}"
    )
    for child in node.get("Plans", []):
        _print_plan_nodes(case, branch, child)


def _print_index_catalog() -> None:
    expected = {(table_name, index_name) for _, table_name, index_name in EXPECTED_SEARCH_INDEXES}
    found: set[tuple[str, str]] = set()
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT tablename, indexname
            FROM pg_indexes
            WHERE schemaname = current_schema()
              AND indexname = ANY(%s)
            """,
            [[index_name for _, _, index_name in EXPECTED_SEARCH_INDEXES]],
        )
        found.update(cursor.fetchall())

    for branch, table_name, index_name in EXPECTED_SEARCH_INDEXES:
        exists = (table_name, index_name) in found
        print(
            f"index_catalog branch={branch} table={table_name} "
            f"index_name={index_name} exists={'yes' if exists else 'no'}"
        )
    if found != expected:
        missing = sorted(expected - found)
        raise RuntimeError(f"BLOCKED: expected search indexes are missing: {missing}")


def _print_plan_summary(case: str, branch: str, plan: dict) -> None:
    scans: list[tuple[str, str]] = []
    _collect_index_usage(plan, scans)
    index_scans = [(scan_type, index_name) for scan_type, index_name in scans if index_name]
    scan_types = ",".join(scan_type for scan_type, _ in scans) or "none"
    index_names = ",".join(index_name for _, index_name in index_scans) or "none"
    print(
        f"case={case} branch={branch} "
        f"plan_scan_types={scan_types} "
        f"plan_index_usage={'yes' if index_scans else 'no'} "
        f"plan_index_names={index_names}"
    )


class PredicateDetectionTests(SimpleTestCase):
    """Focused tests for the SQL/plan predicate report."""

    def test_redacted_plan_filter_reports_full_text_and_trigram_predicates(self) -> None:
        plan = {
            "Node Type": "Seq Scan",
            "Filter": (
                "((search_vector @@ '''<redacted>'''::tsquery) OR "
                "(((title)::text % '<redacted>'::text) OR "
                "((description)::text % '<redacted>'::text)))"
            ),
        }

        summary = _predicate_summary("SELECT ...", plan)

        self.assertTrue(summary.full_text)
        self.assertTrue(summary.trigram)
        self.assertEqual(summary.full_text_source, "plan")
        self.assertEqual(summary.trigram_source, "plan")

    def test_captured_sql_and_plan_sources_are_reported_separately(self) -> None:
        plan = {"Node Type": "Seq Scan", "Filter": "title % '<redacted>'::text"}

        summary = _predicate_summary("SELECT search_vector @@ %s FROM resources_resource", plan)

        self.assertEqual(summary.full_text_source, "sql")
        self.assertEqual(summary.trigram_source, "plan")

    def test_like_and_parameter_placeholders_are_not_trigram_predicates(self) -> None:
        plan = {"Node Type": "Seq Scan", "Filter": "username ~~* '<redacted>'"}

        summary = _predicate_summary("SELECT title LIKE %s FROM auth_user", plan)

        self.assertFalse(summary.full_text)
        self.assertFalse(summary.trigram)


class SearchPlanInspection(TestCase):
    """Capture and explain the four SQL branches used by /api/search/."""

    @classmethod
    def setUpTestData(cls) -> None:
        cls.uploader = User.objects.create_user(username="phase1-plan-uploader")
        now = timezone.now()
        tag = Tag.objects.create(name="Distributed Systems", slug="distributed-systems")

        users = [
            User(
                username=f"phase1-public-user-{index:04d}",
                first_name="Python" if index % MATCH_EVERY == 0 else "General",
                last_name=f"Learner {index:04d}",
                is_active=index % 20 != 0,
                date_joined=now - timedelta(days=index % 180),
            )
            for index in range(PUBLIC_USER_ROWS)
        ]
        users = User.objects.bulk_create(users, batch_size=250)
        StudentProfile.objects.bulk_create(
            [
                StudentProfile(
                    user=user,
                    display_name=(
                        f"Python public learner {index:04d}"
                        if index % MATCH_EVERY == 0
                        else f"General public learner {index:04d}"
                    ),
                    bio=(
                        "Studies Python algorithms and data structures."
                        if index % MATCH_EVERY == 0
                        else "Studies general academic subjects."
                    ),
                    created_at=now - timedelta(days=index % 180),
                    updated_at=now - timedelta(days=index % 180),
                )
                for index, user in enumerate(users)
            ],
            batch_size=250,
        )

        resources = []
        videos = []
        questions = []
        for index in range(CONTENT_ROWS):
            published = index % 5 != 0
            matching = index % MATCH_EVERY == 0
            created_at = now - timedelta(days=index % 90)
            resources.append(
                Resource(
                    title=(
                        f"Python algorithms resource {index:04d}"
                        if matching
                        else f"General study resource {index:04d}"
                    ),
                    slug=f"phase1-plan-resource-{index:04d}",
                    description=(
                        "Published material about Python data structures."
                        if matching
                        else "Published material about general study topics."
                    ),
                    uploader=cls.uploader,
                    subject="Computer Science" if index % 3 else "Mathematics",
                    topic="Algorithms" if matching else "Foundations",
                    course="Measurement Course",
                    semester=str((index % 8) + 1),
                    resource_type=Resource.ResourceType.NOTES,
                    status=PublicationStatus.PUBLISHED if published else PublicationStatus.DRAFT,
                    created_at=created_at,
                    updated_at=created_at,
                )
            )
            videos.append(
                Video(
                    title=(
                        f"Python algorithms video {index:04d}"
                        if matching
                        else f"General study video {index:04d}"
                    ),
                    slug=f"phase1-plan-video-{index:04d}",
                    description=(
                        "Lecture about Python algorithms."
                        if matching
                        else "Lecture about general study topics."
                    ),
                    uploader=cls.uploader,
                    youtube_video_id=f"P1V{index:08d}",
                    subject="Computer Science" if index % 3 else "Mathematics",
                    topic="Algorithms" if matching else "Foundations",
                    course="Measurement Course",
                    semester=str((index % 8) + 1),
                    status=PublicationStatus.PUBLISHED if published else PublicationStatus.DRAFT,
                    created_at=created_at,
                    updated_at=created_at,
                )
            )
            questions.append(
                Question(
                    title=(
                        f"How does Python algorithm {index:04d} work?"
                        if matching
                        else f"How does general topic {index:04d} work?"
                    ),
                    slug=f"phase1-plan-question-{index:04d}",
                    body=(
                        "A question about Python data structures."
                        if matching
                        else "A question about general study topics."
                    ),
                    author=cls.uploader,
                    subject="Computer Science" if index % 3 else "Mathematics",
                    topic="Algorithms" if matching else "Foundations",
                    status=PublicationStatus.PUBLISHED if published else PublicationStatus.DRAFT,
                    created_at=created_at,
                    updated_at=created_at,
                )
            )

        resources = Resource.objects.bulk_create(resources, batch_size=250)
        videos = Video.objects.bulk_create(videos, batch_size=250)
        questions = Question.objects.bulk_create(questions, batch_size=250)
        Resource.tags.through.objects.bulk_create(
            [
                Resource.tags.through(resource_id=row.pk, tag_id=tag.pk)
                for index, row in enumerate(resources)
                if index % TAG_EVERY == 0
            ],
            batch_size=250,
        )
        Video.tags.through.objects.bulk_create(
            [
                Video.tags.through(video_id=row.pk, tag_id=tag.pk)
                for index, row in enumerate(videos)
                if index % TAG_EVERY == 0
            ],
            batch_size=250,
        )
        Question.tags.through.objects.bulk_create(
            [
                Question.tags.through(question_id=row.pk, tag_id=tag.pk)
                for index, row in enumerate(questions)
                if index % TAG_EVERY == 0
            ],
            batch_size=250,
        )

    def _capture_case(self, client: APIClient, case: str, query: str) -> None:
        captured = _SelectCapture()
        with connection.execute_wrapper(captured):
            response = client.get("/api/search/", {"q": query})
        self.assertEqual(response.status_code, 200)

        branch_statements: dict[str, tuple[str, object]] = {}
        for sql, params in captured.statements:
            branch = _branch_for_sql(sql)
            if branch is None:
                continue
            if branch in branch_statements:
                raise RuntimeError("BLOCKED: duplicate SQL branch captured; plan mapping is ambiguous.")
            branch_statements[branch] = (sql, params)

        expected_branches = {branch for branch, _ in BRANCH_TABLES}
        if set(branch_statements) != expected_branches:
            raise RuntimeError("BLOCKED: all four search SQL branches were not captured exactly once.")

        for branch, _ in BRANCH_TABLES:
            sql, params = branch_statements[branch]
            with connection.cursor() as cursor:
                document = _plan_document(cursor, sql, params)
            plan = document[0].get("Plan")
            if not isinstance(plan, dict):
                raise RuntimeError("BLOCKED: PostgreSQL returned an unexpected plan shape.")
            predicates = _predicate_summary(sql, plan)
            print(
                f"predicate_report branch={branch} "
                f"fts_predicate={'yes' if predicates.full_text else 'no'} "
                f"fts_source={predicates.full_text_source} "
                f"trigram_predicate={'yes' if predicates.trigram else 'no'} "
                f"trigram_source={predicates.trigram_source}"
            )
            _print_plan_nodes(case, branch, plan)
            _print_plan_summary(case, branch, plan)

    def test_search_query_plans(self) -> None:
        _print_index_catalog()
        client = APIClient()
        for case, query in (
            ("full-text", "python"),
            ("trigram", "pythn"),
            ("tag-only", "distributed"),
            ("no-match", "qzqxjv"),
        ):
            self._capture_case(client, case, query)
