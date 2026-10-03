from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0003_studentprofile_college"),
    ]

    operations = [
        migrations.AddField(
            model_name="studentprofile",
            name="avatar_reference",
            field=models.CharField(blank=True, max_length=255),
        ),
    ]
