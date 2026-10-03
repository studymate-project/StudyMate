from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiTypes,
    extend_schema,
    extend_schema_view,
    inline_serializer,
)
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet

from apps.core.permissions import IsNotificationRecipient
from apps.core.schema import FORBIDDEN, NOT_FOUND, UNAUTHENTICATED

from .models import Notification
from .serializers import NotificationSerializer


MARK_ALL_READ_RESPONSE = inline_serializer(
    "MarkAllNotificationsReadResponse",
    fields={"updated": serializers.IntegerField(read_only=True)},
)


@extend_schema_view(
    list=extend_schema(
        summary="List notifications",
        description="Return only notifications addressed to the authenticated user, newest first.",
        responses={200: NotificationSerializer(many=True), 401: UNAUTHENTICATED},
    ),
    retrieve=extend_schema(
        summary="Get a notification",
        parameters=[OpenApiParameter("id", OpenApiTypes.INT, OpenApiParameter.PATH)],
        responses={200: NotificationSerializer, 401: UNAUTHENTICATED, 403: FORBIDDEN, 404: NOT_FOUND},
    ),
)
class NotificationViewSet(ReadOnlyModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = (IsAuthenticated, IsNotificationRecipient)

    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user).select_related(
            "recipient", "actor", "content_type"
        ).order_by("-created_at", "-pk")

    @extend_schema(
        summary="Mark one notification as read",
        parameters=[OpenApiParameter("id", OpenApiTypes.INT, OpenApiParameter.PATH)],
        request=None,
        responses={200: NotificationSerializer, 401: UNAUTHENTICATED, 403: FORBIDDEN, 404: NOT_FOUND},
    )
    @action(detail=True, methods=["patch"], url_path="read")
    def mark_read(self, request, *args, **kwargs):
        notification = self.get_object()
        Notification.objects.filter(
            pk=notification.pk,
            recipient=request.user,
            is_read=False,
        ).update(is_read=True)
        notification.is_read = True
        return Response(self.get_serializer(notification).data)

    @extend_schema(
        summary="Mark all notifications as read",
        request=None,
        responses={200: MARK_ALL_READ_RESPONSE, 401: UNAUTHENTICATED},
    )
    @action(detail=False, methods=["patch"], url_path="read-all")
    def mark_all_read(self, request, *args, **kwargs):
        updated = Notification.objects.filter(
            recipient=request.user,
            is_read=False,
        ).update(is_read=True)
        return Response({"updated": updated})
