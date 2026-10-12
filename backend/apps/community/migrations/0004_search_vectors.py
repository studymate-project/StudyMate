import django.contrib.postgres.search
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("community", "0003_question_academic_level_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="question",
            name="search_vector",
            field=django.contrib.postgres.search.SearchVectorField(
                editable=False,
                null=True,
            ),
        ),
    ]
