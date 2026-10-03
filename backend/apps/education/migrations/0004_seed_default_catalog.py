from django.db import migrations


DEFAULT_INTERESTS = (
    ("Java", "java"),
    ("DSA", "dsa"),
    ("DBMS", "dbms"),
    ("Web Development", "web-development"),
    ("Python", "python"),
    ("AI/ML", "ai-ml"),
)


def seed_default_catalog(apps, schema_editor):
    EducationBackground = apps.get_model("education", "EducationBackground")
    Course = apps.get_model("education", "Course")
    AcademicLevel = apps.get_model("education", "AcademicLevel")
    Interest = apps.get_model("education", "Interest")

    background, _ = EducationBackground.objects.get_or_create(
        slug="engineering",
        defaults={
            "name": "Engineering",
            "description": "Engineering and technology programmes.",
            "is_active": True,
        },
    )
    course, _ = Course.objects.get_or_create(
        education_background=background,
        slug="btech",
        defaults={
            "name": "BTech",
            "description": "Bachelor of Technology.",
            "is_active": True,
        },
    )

    for order in range(1, 9):
        ordinal = {1: "1st", 2: "2nd", 3: "3rd"}.get(order, f"{order}th")
        AcademicLevel.objects.get_or_create(
            course=course,
            slug=f"{order}th-semester" if order not in (1, 2, 3) else f"{ordinal.lower()}-semester",
            defaults={
                "name": f"{ordinal} Semester",
                "level_type": "semester",
                "order": order,
                "is_active": True,
            },
        )

    for name, slug in DEFAULT_INTERESTS:
        interest, _ = Interest.objects.get_or_create(
            slug=slug,
            defaults={"name": name, "is_active": True},
        )
        interest.courses.add(course)


class Migration(migrations.Migration):

    dependencies = [
        ("education", "0003_interest_courses"),
    ]

    operations = [
        migrations.RunPython(seed_default_catalog, migrations.RunPython.noop),
    ]
