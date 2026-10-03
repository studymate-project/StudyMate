from django.core.exceptions import ValidationError
from django.db import migrations, models


def normalize_existing_youtube_video_ids(apps, schema_editor):
    from apps.resources.youtube import normalize_youtube_video_id

    Video = apps.get_model("resources", "Video")
    normalized_ids = {}
    updates = []

    for video_id, youtube_video_id in Video.objects.values_list("id", "youtube_video_id").iterator():
        try:
            normalized_video_id = normalize_youtube_video_id(youtube_video_id)
        except ValidationError as error:
            raise RuntimeError(
                f"Video {video_id} has an invalid YouTube video ID and must be corrected before migrating."
            ) from error

        existing_id = normalized_ids.get(normalized_video_id)
        if existing_id is not None and existing_id != video_id:
            raise RuntimeError(
                "Multiple videos normalize to the same YouTube video ID and must be deduplicated before migrating."
            )
        normalized_ids[normalized_video_id] = video_id

        if youtube_video_id != normalized_video_id:
            updates.append((video_id, normalized_video_id))

    for video_id, normalized_video_id in updates:
        Video.objects.filter(pk=video_id).update(youtube_video_id=normalized_video_id)


class Migration(migrations.Migration):
    dependencies = [
        ("resources", "0002_alter_resource_resource_type"),
    ]

    operations = [
        migrations.RunPython(normalize_existing_youtube_video_ids, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="video",
            name="youtube_video_id",
            field=models.CharField(max_length=11, unique=True),
        ),
        migrations.AddConstraint(
            model_name="video",
            constraint=models.CheckConstraint(
                condition=models.Q(("youtube_video_id__regex", "^[A-Za-z0-9_-]{11}$")),
                name="resources_video_youtube_id_format",
            ),
        ),
    ]
