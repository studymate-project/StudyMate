from django.db import transaction
from django.db.models import BooleanField, Count, Exists, OuterRef, Prefetch, Q, Value
from django.shortcuts import get_object_or_404
from rest_framework.generics import ListCreateAPIView, RetrieveDestroyAPIView
from rest_framework.permissions import SAFE_METHODS, AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_201_CREATED
from rest_framework.views import APIView

from apps.core.permissions import IsDiscussionCommentAuthorOrReadOnly
from apps.resources.models import PublicationStatus, Resource, Video

from .models import DiscussionComment, DiscussionCommentLike
from .serializers import DiscussionCommentSerializer


def visible_resource(request, resource_id):
    queryset = Resource.objects.all()
    if request.user.is_authenticated:
        queryset = queryset.filter(Q(status=PublicationStatus.PUBLISHED) | Q(uploader=request.user))
    else:
        queryset = queryset.filter(status=PublicationStatus.PUBLISHED)
    return get_object_or_404(queryset, pk=resource_id)


def visible_video(request, video_slug):
    queryset = Video.objects.all()
    if request.user.is_authenticated:
        queryset = queryset.filter(Q(status=PublicationStatus.PUBLISHED) | Q(uploader=request.user))
    else:
        queryset = queryset.filter(status=PublicationStatus.PUBLISHED)
    return get_object_or_404(queryset, slug=video_slug)


def visible_discussion_queryset(request, target):
    comments = DiscussionComment.objects.select_related("author", "resource", "video")
    if request.user.is_authenticated:
        comments = comments.filter(Q(status=PublicationStatus.PUBLISHED) | Q(author=request.user))
    else:
        comments = comments.filter(status=PublicationStatus.PUBLISHED)

    if isinstance(target, Resource):
        comments = comments.filter(resource=target)
    else:
        comments = comments.filter(video=target)

    if request.user.is_authenticated:
        like_exists = DiscussionCommentLike.objects.filter(comment=OuterRef("pk"), user=request.user)
        comments = comments.annotate(
            like_count=Count("likes", distinct=True),
            liked_by_request_user=Exists(like_exists),
        )
    else:
        comments = comments.annotate(
            like_count=Count("likes", distinct=True),
            liked_by_request_user=Value(False, output_field=BooleanField()),
        )
    return comments


class DiscussionTargetView(ListCreateAPIView):
    serializer_class = DiscussionCommentSerializer
    target_kind = None

    def get_target(self):
        if self.target_kind == "resource":
            return visible_resource(self.request, self.kwargs["resource_id"])
        return visible_video(self.request, self.kwargs["video_slug"])

    def get_permissions(self):
        if self.request.method in SAFE_METHODS:
            return [AllowAny()]
        return [IsAuthenticated()]

    def get_queryset(self):
        target = self.get_target()
        reply_queryset = visible_discussion_queryset(self.request, target).filter(parent__isnull=False)
        return visible_discussion_queryset(self.request, target).filter(parent__isnull=True).prefetch_related(
            Prefetch("replies", queryset=reply_queryset.order_by("created_at", "pk"))
        ).order_by("created_at", "pk")

    def get_serializer_context(self):
        context = super().get_serializer_context()
        target = self.get_target()
        context[self.target_kind] = target
        return context

    def perform_create(self, serializer):
        target = self.get_target()
        save_kwargs = {"author": self.request.user, "status": PublicationStatus.PUBLISHED}
        save_kwargs[self.target_kind] = target
        serializer.save(**save_kwargs)


class ResourceDiscussionView(DiscussionTargetView):
    target_kind = "resource"


class VideoDiscussionView(DiscussionTargetView):
    target_kind = "video"


class DiscussionCommentDetailView(RetrieveDestroyAPIView):
    serializer_class = DiscussionCommentSerializer
    permission_classes = (IsDiscussionCommentAuthorOrReadOnly,)

    def get_permissions(self):
        if self.request.method in SAFE_METHODS:
            return [AllowAny()]
        return [IsAuthenticated(), IsDiscussionCommentAuthorOrReadOnly()]

    def get_queryset(self):
        comments = DiscussionComment.objects.select_related("author", "resource", "video")
        if self.request.user.is_authenticated:
            return comments.filter(Q(status=PublicationStatus.PUBLISHED) | Q(author=self.request.user))
        return comments.filter(status=PublicationStatus.PUBLISHED)


class DiscussionCommentLikeView(APIView):
    permission_classes = (IsAuthenticated,)

    def get_comment(self, request, pk):
        return get_object_or_404(DiscussionComment.objects.filter(status=PublicationStatus.PUBLISHED), pk=pk)

    @staticmethod
    def response_data(comment, liked):
        return {
            "comment": comment.pk,
            "liked": liked,
            "like_count": comment.likes.count(),
        }

    @transaction.atomic
    def post(self, request, pk):
        comment = self.get_comment(request, pk)
        _, created = DiscussionCommentLike.objects.get_or_create(comment=comment, user=request.user)
        return Response(self.response_data(comment, True), status=HTTP_201_CREATED if created else HTTP_200_OK)

    @transaction.atomic
    def delete(self, request, pk):
        comment = self.get_comment(request, pk)
        DiscussionCommentLike.objects.filter(comment=comment, user=request.user).delete()
        return Response(self.response_data(comment, False), status=HTTP_200_OK)
