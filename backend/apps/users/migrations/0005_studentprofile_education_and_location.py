from django.db import migrations, models


def backfill_academic_stage(apps, schema_editor):
    StudentProfile = apps.get_model("users", "StudentProfile")
    for profile in StudentProfile.objects.select_related("academic_level").filter(
        academic_level__isnull=False
    ):
        profile.academic_level_type = profile.academic_level.level_type
        profile.academic_level_value = profile.academic_level.name
        profile.save(update_fields=("academic_level_type", "academic_level_value"))


class Migration(migrations.Migration):
    dependencies = [
        ("education", "0006_seed_education_catalog"),
        ("users", "0004_studentprofile_avatar_reference"),
    ]

    operations = [
        migrations.AddField(
            model_name="studentprofile",
            name="country",
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name="studentprofile",
            name="state",
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name="studentprofile",
            name="city",
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name="studentprofile",
            name="custom_background",
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name="studentprofile",
            name="custom_course",
            field=models.CharField(blank=True, max_length=160),
        ),
        migrations.AddField(
            model_name="studentprofile",
            name="academic_level_type",
            field=models.CharField(
                blank=True,
                choices=[
                    ("class", "Class"),
                    ("semester", "Semester"),
                    ("year", "Year"),
                    ("level", "Level"),
                    ("stage", "Stage"),
                    ("other", "Other"),
                ],
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name="studentprofile",
            name="academic_level_value",
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.RunPython(backfill_academic_stage, migrations.RunPython.noop),
    ]
