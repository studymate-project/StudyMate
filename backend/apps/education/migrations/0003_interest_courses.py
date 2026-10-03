from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("education", "0002_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="interest",
            name="courses",
            field=models.ManyToManyField(blank=True, related_name="interests", to="education.course"),
        ),
    ]
