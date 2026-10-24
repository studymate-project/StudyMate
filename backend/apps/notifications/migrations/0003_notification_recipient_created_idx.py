from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("notifications", "0002_notification_notification_type_is_supported"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="notification",
            index=models.Index(
                fields=["recipient", "-created_at", "-id"],
                name="notif_recipient_created_idx",
            ),
        ),
    ]
