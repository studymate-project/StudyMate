from django.urls import path

from .discussion_views import (
    DiscussionCommentDetailView,
    DiscussionCommentLikeView,
    ResourceDiscussionView,
    VideoDiscussionView,
)


urlpatterns = [
    path("resources/<int:resource_id>/", ResourceDiscussionView.as_view(), name="resource-discussion"),
    path("videos/<slug:video_slug>/", VideoDiscussionView.as_view(), name="video-discussion"),
    path("comments/<int:pk>/", DiscussionCommentDetailView.as_view(), name="discussion-comment-detail"),
    path("comments/<int:pk>/like/", DiscussionCommentLikeView.as_view(), name="discussion-comment-like"),
]
