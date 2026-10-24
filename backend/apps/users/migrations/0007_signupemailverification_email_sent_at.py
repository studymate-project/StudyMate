from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0006_signupemailverification"),
    ]

    operations = [
        migrations.AddField(
            model_name="signupemailverification",
            name="email_sent_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
