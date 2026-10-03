from django.db import migrations


def normalize_default_course_name(apps, schema_editor):
    EducationBackground = apps.get_model("education", "EducationBackground")
    Course = apps.get_model("education", "Course")

    background = EducationBackground.objects.filter(slug="engineering").first()
    if background is not None:
        Course.objects.filter(
            education_background=background,
            slug="btech",
            name="B.Tech",
        ).update(name="BTech")


class Migration(migrations.Migration):

    dependencies = [
        ("education", "0004_seed_default_catalog"),
    ]

    operations = [
        migrations.RunPython(normalize_default_course_name, migrations.RunPython.noop),
    ]
