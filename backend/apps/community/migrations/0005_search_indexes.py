from django.contrib.postgres.indexes import GinIndex
from django.db import migrations


QUESTION_SEARCH_SQL = """
CREATE OR REPLACE FUNCTION studymate_community_question_search_vector()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    tag_text text;
BEGIN
    SELECT string_agg(concat_ws(' ', tag.name, tag.slug), ' ')
    INTO tag_text
    FROM resources_tag AS tag
    INNER JOIN community_question_tags AS relation ON relation.tag_id = tag.id
    WHERE relation.question_id = NEW.id;

    NEW.search_vector :=
        setweight(to_tsvector('pg_catalog.english', coalesce(NEW.title, '')), 'A') ||
        setweight(to_tsvector('pg_catalog.english', coalesce(NEW.body, '')), 'B') ||
        setweight(
            to_tsvector(
                'pg_catalog.english',
                concat_ws(' ', NEW.subject, NEW.topic)
            ),
            'C'
        ) ||
        setweight(to_tsvector('pg_catalog.english', coalesce(tag_text, '')), 'B');
    RETURN NEW;
END;
$$;

CREATE OR REPLACE FUNCTION studymate_community_question_tags_search_vector()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF TG_OP = 'UPDATE' AND OLD.question_id IS DISTINCT FROM NEW.question_id THEN
        UPDATE community_question AS question_row
        SET title = question_row.title
        WHERE question_row.id = OLD.question_id;
    END IF;

    UPDATE community_question AS question_row
    SET title = question_row.title
    WHERE question_row.id = COALESCE(NEW.question_id, OLD.question_id);
    RETURN NULL;
END;
$$;

CREATE OR REPLACE FUNCTION studymate_resources_tag_search_vector()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    UPDATE resources_resource AS resource_row
    SET title = resource_row.title
    WHERE EXISTS (
        SELECT 1
        FROM resources_resource_tags AS relation
        WHERE relation.resource_id = resource_row.id AND relation.tag_id = NEW.id
    );

    UPDATE resources_video AS video_row
    SET title = video_row.title
    WHERE EXISTS (
        SELECT 1
        FROM resources_video_tags AS relation
        WHERE relation.video_id = video_row.id AND relation.tag_id = NEW.id
    );

    UPDATE community_question AS question_row
    SET title = question_row.title
    WHERE EXISTS (
        SELECT 1
        FROM community_question_tags AS relation
        WHERE relation.question_id = question_row.id AND relation.tag_id = NEW.id
    );
    RETURN NULL;
END;
$$;

CREATE TRIGGER community_question_search_vector_biu
BEFORE INSERT OR UPDATE ON community_question
FOR EACH ROW EXECUTE FUNCTION studymate_community_question_search_vector();

CREATE TRIGGER community_question_tags_search_vector_aiud
AFTER INSERT OR UPDATE OR DELETE ON community_question_tags
FOR EACH ROW EXECUTE FUNCTION studymate_community_question_tags_search_vector();

CREATE TRIGGER resources_tag_search_vector_au
AFTER UPDATE OF name, slug ON resources_tag
FOR EACH ROW EXECUTE FUNCTION studymate_resources_tag_search_vector();

UPDATE community_question
SET search_vector = search_vector
WHERE search_vector IS NULL;
"""

QUESTION_SEARCH_REVERSE_SQL = """
DROP TRIGGER IF EXISTS resources_tag_search_vector_au ON resources_tag;
DROP TRIGGER IF EXISTS community_question_tags_search_vector_aiud ON community_question_tags;
DROP TRIGGER IF EXISTS community_question_search_vector_biu ON community_question;
DROP FUNCTION IF EXISTS studymate_resources_tag_search_vector();
DROP FUNCTION IF EXISTS studymate_community_question_tags_search_vector();
DROP FUNCTION IF EXISTS studymate_community_question_search_vector();
"""


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("community", "0004_search_vectors"),
        ("resources", "0007_search_indexes"),
    ]

    operations = [
        migrations.RunSQL(QUESTION_SEARCH_SQL, QUESTION_SEARCH_REVERSE_SQL),
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    "CREATE INDEX CONCURRENTLY community_question_search_fts "
                    "ON community_question USING gin (search_vector)",
                    "DROP INDEX CONCURRENTLY IF EXISTS community_question_search_fts",
                ),
                migrations.RunSQL(
                    "CREATE INDEX CONCURRENTLY community_question_search_trgm "
                    "ON community_question USING gin "
                    "(title gin_trgm_ops, body gin_trgm_ops, subject gin_trgm_ops, topic gin_trgm_ops)",
                    "DROP INDEX CONCURRENTLY IF EXISTS community_question_search_trgm",
                ),
            ],
            state_operations=[
                migrations.AddIndex(
                    model_name="question",
                    index=GinIndex(
                        fields=("search_vector",),
                        name="community_question_search_fts",
                    ),
                ),
                migrations.AddIndex(
                    model_name="question",
                    index=GinIndex(
                        fields=("title", "body", "subject", "topic"),
                        name="community_question_search_trgm",
                        opclasses=("gin_trgm_ops",) * 4,
                    ),
                ),
            ],
        ),
    ]
