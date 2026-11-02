from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("resources", "0007_search_indexes"),
    ]

    operations = [
        migrations.AlterField(
            model_name="resource",
            name="subject",
            field=models.CharField(blank=True, db_index=True, default="", max_length=120),
        ),
        migrations.AlterField(
            model_name="resource",
            name="topic",
            field=models.CharField(blank=True, db_index=True, default="", max_length=120),
        ),
        migrations.AlterField(
            model_name="resource",
            name="course",
            field=models.CharField(blank=True, db_index=True, default="", max_length=160),
        ),
        migrations.AlterField(
            model_name="resource",
            name="semester",
            field=models.CharField(blank=True, db_index=True, default="", max_length=80),
        ),
        migrations.AlterField(
            model_name="video",
            name="subject",
            field=models.CharField(blank=True, db_index=True, default="", max_length=120),
        ),
        migrations.AlterField(
            model_name="video",
            name="topic",
            field=models.CharField(blank=True, db_index=True, default="", max_length=120),
        ),
        migrations.AlterField(
            model_name="video",
            name="course",
            field=models.CharField(blank=True, db_index=True, default="", max_length=160),
        ),
        migrations.AlterField(
            model_name="video",
            name="semester",
            field=models.CharField(blank=True, db_index=True, default="", max_length=80),
        ),
    ]
