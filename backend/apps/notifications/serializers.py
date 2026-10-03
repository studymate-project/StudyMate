from rest_framework import serializers

from apps.users.serializers import PublicUserSerializer

from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    recipient = PublicUserSerializer(read_only=True)
    actor = PublicUserSerializer(read_only=True)

    class Meta:
        model = Notification
        fields = (
            "id",
            "recipient",
            "actor",
            "notification_type",
            "content_type",
            "object_id",
            "message",
            "payload",
            "is_read",
            "created_at",
        )
        read_only_fields = ("id", "recipient", "actor", "content_type", "object_id", "created_at")
