from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("resources", "0003_normalize_youtube_video_id"),
    ]

    operations = [
        migrations.AddField(
            model_name="resource",
            name="client_upload_id",
            field=models.UUIDField(blank=True, default=None, editable=False, null=True, unique=True),
        ),
    ]
