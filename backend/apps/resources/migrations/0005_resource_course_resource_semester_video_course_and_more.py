from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("resources", "0004_resource_client_upload_id"),
    ]

    operations = [
        migrations.AlterField(
            model_name="resource",
            name="resource_type",
            field=models.CharField(
                choices=[
                    ("file", "File"),
                    ("video", "Video"),
                    ("notes", "Notes"),
                    ("pdf", "PDF"),
                    ("cheat_sheet", "Cheat sheet"),
                    ("presentation", "Presentation"),
                    ("assignment", "Assignment"),
                    ("question_paper", "Question paper"),
                    ("study_guide", "Study guide"),
                    ("link", "Link"),
                    ("other", "Other"),
                ],
                db_index=True,
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="resource",
            name="course",
            field=models.CharField(blank=True, db_index=True, max_length=160),
        ),
        migrations.AddField(
            model_name="resource",
            name="semester",
            field=models.CharField(blank=True, db_index=True, max_length=80),
        ),
        migrations.AddField(
            model_name="video",
            name="course",
            field=models.CharField(blank=True, db_index=True, max_length=160),
        ),
        migrations.AddField(
            model_name="video",
            name="semester",
            field=models.CharField(blank=True, db_index=True, max_length=80),
        ),
    ]
