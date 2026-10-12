import django.contrib.postgres.search
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("resources", "0005_resource_course_resource_semester_video_course_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="resource",
            name="search_vector",
            field=django.contrib.postgres.search.SearchVectorField(
                editable=False,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="video",
            name="search_vector",
            field=django.contrib.postgres.search.SearchVectorField(
                editable=False,
                null=True,
            ),
        ),
    ]
