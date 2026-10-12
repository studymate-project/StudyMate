import importlib

from django.contrib.auth.models import User
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchQuery, SearchVectorField
from django.db import migrations
from django.test import SimpleTestCase, TestCase

from apps.community.models import Question
from apps.resources.models import PublicationStatus, Resource, Tag, Video


class SearchFoundationConfigurationTests(SimpleTestCase):
    def test_search_vector_fields_and_indexes_are_declared_for_searchable_models(self):
        expected_indexes = {
            Resource: {
                "resources_resource_search_fts",
                "resources_resource_search_trgm",
            },
            Video: {
                "resources_video_search_fts",
                "resources_video_search_trgm",
            },
            Question: {
                "community_question_search_fts",
                "community_question_search_trgm",
            },
        }

        for model, index_names in expected_indexes.items():
            with self.subTest(model=model.__name__):
                self.assertIsInstance(model._meta.get_field("search_vector"), SearchVectorField)
                self.assertTrue(index_names <= {index.name for index in model._meta.indexes})

    def test_answer_is_not_given_an_unjustified_search_vector(self):
        from apps.community.models import Answer

        self.assertNotIn("search_vector", {field.name for field in Answer._meta.local_fields})

    def test_search_indexes_are_concurrent_and_reversible(self):
        resources_migration = importlib.import_module("apps.resources.migrations.0007_search_indexes")
        community_migration = importlib.import_module("apps.community.migrations.0005_search_indexes")

        for migration_module in (resources_migration, community_migration):
            with self.subTest(migration=migration_module.__name__):
                self.assertFalse(migration_module.Migration.atomic)
                database_operations = []
                for operation in migration_module.Migration.operations:
                    if isinstance(operation, migrations.SeparateDatabaseAndState):
                        database_operations.extend(operation.database_operations)
                    elif isinstance(operation, migrations.RunSQL):
                        database_operations.append(operation)

                index_sql = [
                    operation.sql
                    for operation in database_operations
                    if isinstance(operation, migrations.RunSQL) and isinstance(operation.sql, str)
                ]
                self.assertTrue(any("CREATE INDEX CONCURRENTLY" in sql for sql in index_sql))
                self.assertTrue(
                    all(
                        operation.reverse_sql
                        for operation in database_operations
                        if isinstance(operation, migrations.RunSQL)
                    )
                )

        self.assertTrue(
            any(
                operation.__class__.__name__ == "TrigramExtension"
                for operation in resources_migration.Migration.operations
            )
        )


class SearchVectorTriggerTests(TestCase):
    @staticmethod
    def _has_term(model, instance_id, term):
        return model.objects.filter(pk=instance_id, search_vector=SearchQuery(term)).exists()

    def setUp(self):
        self.user = User.objects.create_user(username="search-foundation-user", password="not-used-in-test")

    def test_resource_vector_tracks_metadata_and_tag_changes(self):
        resource = Resource.objects.create(
            title="Linear algebra notes",
            description="Matrix multiplication and eigenvalues",
            uploader=self.user,
            subject="Mathematics",
            topic="Algebra",
            course="BTech",
            semester="Semester 1",
            resource_type=Resource.ResourceType.NOTES,
            status=PublicationStatus.PUBLISHED,
        )

        self.assertTrue(self._has_term(Resource, resource.pk, "linear"))
        self.assertTrue(self._has_term(Resource, resource.pk, "eigenvalues"))

        tag = Tag.objects.create(name="Matrix Theory", slug="matrix-theory")
        resource.tags.add(tag)
        self.assertTrue(self._has_term(Resource, resource.pk, "matrix"))

        resource.title = "Calculus notes"
        resource.save(update_fields=("title",))
        self.assertTrue(self._has_term(Resource, resource.pk, "calculus"))
        self.assertFalse(self._has_term(Resource, resource.pk, "linear"))

    def test_video_vector_tracks_course_and_question_vector_tracks_body(self):
        video = Video.objects.create(
            title="Python recursion lecture",
            description="A lecture about recursive functions",
            uploader=self.user,
            youtube_video_id="dQw4w9WgXcQ",
            subject="Computer Science",
            topic="Algorithms",
            course="BTech",
            semester="Semester 2",
            status=PublicationStatus.PUBLISHED,
        )
        self.assertTrue(self._has_term(Video, video.pk, "recursion"))
        self.assertTrue(self._has_term(Video, video.pk, "btech"))

        question = Question.objects.create(
            title="How does recursion terminate?",
            body="I need help understanding the base case.",
            author=self.user,
            subject="Computer Science",
            topic="Algorithms",
        )
        self.assertTrue(self._has_term(Question, question.pk, "terminate"))
        self.assertTrue(self._has_term(Question, question.pk, "base"))

        question.body = "I need help understanding recursive induction."
        question.save(update_fields=("body",))
        self.assertTrue(self._has_term(Question, question.pk, "recursive"))
        self.assertFalse(self._has_term(Question, question.pk, "base"))
