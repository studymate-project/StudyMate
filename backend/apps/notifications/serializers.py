from urllib.parse import quote, urlsplit

from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.community.models import Answer, Question
from apps.resources.models import PublicationStatus, Resource, Video
from apps.users.serializers import PublicUserSerializer

from .models import Notification


class NotificationListSerializer(serializers.ListSerializer):
    """Batch generic notification targets before serializing a list."""

    def to_representation(self, data):
        items = list(data.all()) if hasattr(data, "all") else list(data)
        self.child.prefetch_targets(items)
        return super().to_representation(items)


class NotificationSerializer(serializers.ModelSerializer):
    recipient = PublicUserSerializer(read_only=True)
    actor = PublicUserSerializer(read_only=True)
    target = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        list_serializer_class = NotificationListSerializer
        fields = (
            "id",
            "recipient",
            "actor",
            "notification_type",
            "content_type",
            "object_id",
            "message",
            "payload",
            "target",
            "is_read",
            "created_at",
        )
        read_only_fields = ("id", "recipient", "actor", "content_type", "object_id", "created_at")

    @staticmethod
    def prefetch_targets(notifications):
        targets_by_model = {}
        for notification in notifications:
            content_type = notification.content_type
            model = content_type.model_class() if content_type is not None else None
            if model is not None and notification.object_id is not None:
                targets_by_model.setdefault(model, set()).add(notification.object_id)

        user_model = get_user_model()
        querysets = {}
        if Resource in targets_by_model:
            querysets[Resource] = Resource.objects.filter(pk__in=targets_by_model[Resource])
        if Video in targets_by_model:
            querysets[Video] = Video.objects.filter(pk__in=targets_by_model[Video])
        if Question in targets_by_model:
            querysets[Question] = Question.objects.filter(pk__in=targets_by_model[Question])
        if Answer in targets_by_model:
            querysets[Answer] = Answer.objects.select_related("question").filter(
                pk__in=targets_by_model[Answer]
            )
        if user_model in targets_by_model:
            querysets[user_model] = user_model.objects.filter(pk__in=targets_by_model[user_model])
        objects_by_key = {}
        for model, queryset in querysets.items():
            objects_by_key.update({(model, obj.pk): obj for obj in queryset})

        for notification in notifications:
            content_type = notification.content_type
            model = content_type.model_class() if content_type is not None else None
            setattr(
                notification,
                "_prefetched_notification_target",
                objects_by_key.get((model, notification.object_id)),
            )

    def _request_user(self):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        return user if getattr(user, "is_authenticated", False) else None

    def _visible(self, instance, *, owner_field: str) -> bool:
        if getattr(instance, "status", None) == PublicationStatus.PUBLISHED:
            return True
        user = self._request_user()
        return bool(user and getattr(instance, f"{owner_field}_id", None) == user.pk)

    @staticmethod
    def _internal_target(kind: str, url: str, *, resource_type: str | None = None) -> dict[str, str]:
        target = {"kind": kind, "url": url}
        if resource_type:
            target["resource_type"] = resource_type
        return target

    @staticmethod
    def _external_target(url: str, resource_type: str) -> dict[str, str] | None:
        parsed = urlsplit(url)
        if parsed.scheme.casefold() not in {"http", "https"} or not parsed.netloc:
            return None
        if parsed.username or parsed.password:
            return None
        return {"kind": "external", "url": url, "resource_type": resource_type}

    def get_target(self, notification):
        content_type = notification.content_type
        if content_type is None or notification.object_id is None:
            return None

        model = content_type.model_class()
        if model is Resource:
            resource = getattr(notification, "_prefetched_notification_target", None)
            if not hasattr(notification, "_prefetched_notification_target"):
                resource = Resource.objects.filter(pk=notification.object_id).first()
            if resource is None or not self._visible(resource, owner_field="uploader"):
                return None
            if resource.resource_type == Resource.ResourceType.LINK:
                return self._external_target(resource.external_url, resource.resource_type)
            return self._internal_target(
                "resource",
                f"/resources/{quote(resource.slug, safe='')}",
                resource_type=resource.resource_type,
            )

        if model is Video:
            video = getattr(notification, "_prefetched_notification_target", None)
            if not hasattr(notification, "_prefetched_notification_target"):
                video = Video.objects.filter(pk=notification.object_id).first()
            if video is None or not self._visible(video, owner_field="uploader"):
                return None
            return self._internal_target("video", f"/videos/{quote(video.slug, safe='')}", resource_type="video")

        if model is Question:
            question = getattr(notification, "_prefetched_notification_target", None)
            if not hasattr(notification, "_prefetched_notification_target"):
                question = Question.objects.filter(pk=notification.object_id).first()
            if question is None or not self._visible(question, owner_field="author"):
                return None
            return self._internal_target("question", f"/questions/{quote(question.slug, safe='')}")

        if model is Answer:
            answer = getattr(notification, "_prefetched_notification_target", None)
            if not hasattr(notification, "_prefetched_notification_target"):
                answer = Answer.objects.select_related("question").filter(pk=notification.object_id).first()
            if answer is None or not self._visible(answer.question, owner_field="author"):
                return None
            return self._internal_target("question", f"/questions/{quote(answer.question.slug, safe='')}")

        user_model = get_user_model()
        if model is user_model:
            user = getattr(notification, "_prefetched_notification_target", None)
            if not hasattr(notification, "_prefetched_notification_target"):
                user = user_model.objects.filter(pk=notification.object_id).first()
            if user is None:
                return None
            return self._internal_target("profile", f"/users/{quote(user.username, safe='')}")

        return None
