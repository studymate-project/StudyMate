from django.db import migrations


BACKGROUND_SPECS = (
    ("engineering", "Engineering", "Engineering and technology programmes."),
    ("medicine-healthcare", "Medicine/Healthcare", "Medicine and healthcare programmes."),
    ("science", "Science", "Natural and applied science programmes."),
    ("commerce", "Commerce", "Accounting, finance, and commerce programmes."),
    ("arts-humanities", "Arts/Humanities", "Arts, languages, and humanities programmes."),
    ("law", "Law", "Legal studies and law programmes."),
    ("school", "School", "Class-based school education."),
    ("vocational-professional", "Vocational/Professional", "Vocational and professional programmes."),
    ("other", "Other", "A flexible category for education backgrounds not listed above."),
)

COURSE_SPECS = (
    ("engineering", "btech", "BTech", "Bachelor of Technology.", "semester", 8),
    ("engineering", "be", "B.E.", "Bachelor of Engineering.", "semester", 8),
    ("engineering", "mtech", "MTech", "Master of Technology.", "semester", 4),
    ("medicine-healthcare", "mbbs", "MBBS", "Bachelor of Medicine and Bachelor of Surgery.", "year", 5),
    ("medicine-healthcare", "nursing", "Nursing", "Professional nursing programme.", "year", 4),
    ("science", "bsc", "BSc", "Bachelor of Science.", "year", 3),
    ("commerce", "bcom", "BCom", "Bachelor of Commerce.", "year", 3),
    ("arts-humanities", "ba", "BA", "Bachelor of Arts.", "year", 3),
    ("arts-humanities", "ma", "MA", "Master of Arts.", "year", 2),
    ("law", "llb", "LLB", "Bachelor of Laws.", "year", 3),
    ("law", "llm", "LLM", "Master of Laws.", "year", 2),
    ("school", "school-class", "Class-based Education", "School education organised by class.", "class", 12),
    ("vocational-professional", "diploma", "Diploma", "Diploma and technical training.", "level", 3),
    ("vocational-professional", "certificate", "Certificate", "Certificate and professional training.", "level", 2),
    ("other", "other", "Other", "A flexible programme for custom education selections.", None, 0),
)


def _get_or_create_background(background_model, slug, name, description):
    background = background_model.objects.filter(slug=slug).first()
    if background is None:
        background = background_model.objects.filter(name__iexact=name).first()
    if background is None:
        background = background_model.objects.create(
            slug=slug,
            name=name,
            description=description,
            is_active=True,
        )
    return background


def _get_or_create_course(course_model, background, slug, name, description):
    course = course_model.objects.filter(education_background=background, slug=slug).first()
    if course is None:
        course = course_model.objects.filter(
            education_background=background, name__iexact=name
        ).first()
    if course is None:
        course = course_model.objects.create(
            education_background=background,
            slug=slug,
            name=name,
            description=description,
            is_active=True,
        )
    return course


def _get_or_create_level(level_model, course, level_type, order, name):
    slug = f"{order}-{level_type}"
    level = level_model.objects.filter(course=course, slug=slug).first()
    if level is None:
        level = level_model.objects.filter(course=course, name__iexact=name).first()
    if level is None:
        level = level_model.objects.create(
            course=course,
            name=name,
            slug=slug,
            level_type=level_type,
            order=order,
            is_active=True,
        )
    return level


def seed_catalog(apps, schema_editor):
    EducationBackground = apps.get_model("education", "EducationBackground")
    Course = apps.get_model("education", "Course")
    AcademicLevel = apps.get_model("education", "AcademicLevel")

    backgrounds = {
        slug: _get_or_create_background(EducationBackground, slug, name, description)
        for slug, name, description in BACKGROUND_SPECS
    }

    for background_slug, course_slug, name, description, level_type, level_count in COURSE_SPECS:
        course = _get_or_create_course(
            Course,
            backgrounds[background_slug],
            course_slug,
            name,
            description,
        )
        if not level_type:
            continue
        for order in range(1, level_count + 1):
            if level_type == "semester":
                ordinal = {1: "1st", 2: "2nd", 3: "3rd"}.get(order, f"{order}th")
                level_name = f"{ordinal} Semester"
            elif level_type == "class":
                level_name = f"Class {order}"
            elif level_type == "year":
                ordinal = {1: "1st", 2: "2nd", 3: "3rd"}.get(order, f"{order}th")
                level_name = f"{ordinal} Year"
            else:
                level_name = f"Level {order}"
            _get_or_create_level(AcademicLevel, course, level_type, order, level_name)


class Migration(migrations.Migration):
    dependencies = [("education", "0005_normalize_default_course_name")]

    operations = [migrations.RunPython(seed_catalog, migrations.RunPython.noop)]
