from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.operations import TrigramExtension
from django.db import migrations


RESOURCE_SEARCH_SQL = """
CREATE OR REPLACE FUNCTION studymate_resources_resource_search_vector()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    tag_text text;
BEGIN
    SELECT string_agg(concat_ws(' ', tag.name, tag.slug), ' ')
    INTO tag_text
    FROM resources_tag AS tag
    INNER JOIN resources_resource_tags AS relation ON relation.tag_id = tag.id
    WHERE relation.resource_id = NEW.id;

    NEW.search_vector :=
        setweight(to_tsvector('pg_catalog.english', coalesce(NEW.title, '')), 'A') ||
        setweight(to_tsvector('pg_catalog.english', coalesce(NEW.description, '')), 'B') ||
        setweight(
            to_tsvector(
                'pg_catalog.english',
                concat_ws(' ', NEW.subject, NEW.topic, NEW.course, NEW.semester)
            ),
            'C'
        ) ||
        setweight(to_tsvector('pg_catalog.english', coalesce(tag_text, '')), 'B');
    RETURN NEW;
END;
$$;

CREATE OR REPLACE FUNCTION studymate_resources_video_search_vector()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    tag_text text;
BEGIN
    SELECT string_agg(concat_ws(' ', tag.name, tag.slug), ' ')
    INTO tag_text
    FROM resources_tag AS tag
    INNER JOIN resources_video_tags AS relation ON relation.tag_id = tag.id
    WHERE relation.video_id = NEW.id;

    NEW.search_vector :=
        setweight(to_tsvector('pg_catalog.english', coalesce(NEW.title, '')), 'A') ||
        setweight(to_tsvector('pg_catalog.english', coalesce(NEW.description, '')), 'B') ||
        setweight(
            to_tsvector(
                'pg_catalog.english',
                concat_ws(' ', NEW.subject, NEW.topic, NEW.course, NEW.semester)
            ),
            'C'
        ) ||
        setweight(to_tsvector('pg_catalog.english', coalesce(tag_text, '')), 'B');
    RETURN NEW;
END;
$$;

CREATE OR REPLACE FUNCTION studymate_resources_resource_tags_search_vector()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF TG_OP = 'UPDATE' AND OLD.resource_id IS DISTINCT FROM NEW.resource_id THEN
        UPDATE resources_resource AS resource_row
        SET title = resource_row.title
        WHERE resource_row.id = OLD.resource_id;
    END IF;

    UPDATE resources_resource AS resource_row
    SET title = resource_row.title
    WHERE resource_row.id = COALESCE(NEW.resource_id, OLD.resource_id);
    RETURN NULL;
END;
$$;

CREATE OR REPLACE FUNCTION studymate_resources_video_tags_search_vector()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF TG_OP = 'UPDATE' AND OLD.video_id IS DISTINCT FROM NEW.video_id THEN
        UPDATE resources_video AS video_row
        SET title = video_row.title
        WHERE video_row.id = OLD.video_id;
    END IF;

    UPDATE resources_video AS video_row
    SET title = video_row.title
    WHERE video_row.id = COALESCE(NEW.video_id, OLD.video_id);
    RETURN NULL;
END;
$$;

CREATE TRIGGER resources_resource_search_vector_biu
BEFORE INSERT OR UPDATE ON resources_resource
FOR EACH ROW EXECUTE FUNCTION studymate_resources_resource_search_vector();

CREATE TRIGGER resources_video_search_vector_biu
BEFORE INSERT OR UPDATE ON resources_video
FOR EACH ROW EXECUTE FUNCTION studymate_resources_video_search_vector();

CREATE TRIGGER resources_resource_tags_search_vector_aiud
AFTER INSERT OR UPDATE OR DELETE ON resources_resource_tags
FOR EACH ROW EXECUTE FUNCTION studymate_resources_resource_tags_search_vector();

CREATE TRIGGER resources_video_tags_search_vector_aiud
AFTER INSERT OR UPDATE OR DELETE ON resources_video_tags
FOR EACH ROW EXECUTE FUNCTION studymate_resources_video_tags_search_vector();

UPDATE resources_resource
SET search_vector = search_vector
WHERE search_vector IS NULL;

UPDATE resources_video
SET search_vector = search_vector
WHERE search_vector IS NULL;
"""

RESOURCE_SEARCH_REVERSE_SQL = """
DROP TRIGGER IF EXISTS resources_video_tags_search_vector_aiud ON resources_video_tags;
DROP TRIGGER IF EXISTS resources_resource_tags_search_vector_aiud ON resources_resource_tags;
DROP TRIGGER IF EXISTS resources_video_search_vector_biu ON resources_video;
DROP TRIGGER IF EXISTS resources_resource_search_vector_biu ON resources_resource;
DROP FUNCTION IF EXISTS studymate_resources_video_tags_search_vector();
DROP FUNCTION IF EXISTS studymate_resources_resource_tags_search_vector();
DROP FUNCTION IF EXISTS studymate_resources_video_search_vector();
DROP FUNCTION IF EXISTS studymate_resources_resource_search_vector();
"""


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("resources", "0006_search_vectors"),
    ]

    operations = [
        TrigramExtension(),
        migrations.RunSQL(RESOURCE_SEARCH_SQL, RESOURCE_SEARCH_REVERSE_SQL),
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    "CREATE INDEX CONCURRENTLY resources_resource_search_fts "
                    "ON resources_resource USING gin (search_vector)",
                    "DROP INDEX CONCURRENTLY IF EXISTS resources_resource_search_fts",
                ),
                migrations.RunSQL(
                    "CREATE INDEX CONCURRENTLY resources_resource_search_trgm "
                    "ON resources_resource USING gin "
                    "(title gin_trgm_ops, description gin_trgm_ops, subject gin_trgm_ops, "
                    "topic gin_trgm_ops, course gin_trgm_ops, semester gin_trgm_ops)",
                    "DROP INDEX CONCURRENTLY IF EXISTS resources_resource_search_trgm",
                ),
                migrations.RunSQL(
                    "CREATE INDEX CONCURRENTLY resources_video_search_fts "
                    "ON resources_video USING gin (search_vector)",
                    "DROP INDEX CONCURRENTLY IF EXISTS resources_video_search_fts",
                ),
                migrations.RunSQL(
                    "CREATE INDEX CONCURRENTLY resources_video_search_trgm "
                    "ON resources_video USING gin "
                    "(title gin_trgm_ops, description gin_trgm_ops, subject gin_trgm_ops, "
                    "topic gin_trgm_ops, course gin_trgm_ops, semester gin_trgm_ops)",
                    "DROP INDEX CONCURRENTLY IF EXISTS resources_video_search_trgm",
                ),
                migrations.RunSQL(
                    "CREATE INDEX CONCURRENTLY resources_tag_search_trgm "
                    "ON resources_tag USING gin (name gin_trgm_ops, slug gin_trgm_ops)",
                    "DROP INDEX CONCURRENTLY IF EXISTS resources_tag_search_trgm",
                ),
            ],
            state_operations=[
                migrations.AddIndex(
                    model_name="resource",
                    index=GinIndex(
                        fields=("search_vector",),
                        name="resources_resource_search_fts",
                    ),
                ),
                migrations.AddIndex(
                    model_name="resource",
                    index=GinIndex(
                        fields=("title", "description", "subject", "topic", "course", "semester"),
                        name="resources_resource_search_trgm",
                        opclasses=("gin_trgm_ops",) * 6,
                    ),
                ),
                migrations.AddIndex(
                    model_name="video",
                    index=GinIndex(
                        fields=("search_vector",),
                        name="resources_video_search_fts",
                    ),
                ),
                migrations.AddIndex(
                    model_name="video",
                    index=GinIndex(
                        fields=("title", "description", "subject", "topic", "course", "semester"),
                        name="resources_video_search_trgm",
                        opclasses=("gin_trgm_ops",) * 6,
                    ),
                ),
                migrations.AddIndex(
                    model_name="tag",
                    index=GinIndex(
                        fields=("name", "slug"),
                        name="resources_tag_search_trgm",
                        opclasses=("gin_trgm_ops",) * 2,
                    ),
                ),
            ],
        ),
    ]
