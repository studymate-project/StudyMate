from rest_framework.routers import DefaultRouter

from django.urls import path

from .views import (
    ResourceDownloadTrackView,
    ResourceRatingView,
    ResourceSaveView,
    ResourceUpvoteView,
    ResourceViewSet,
    ResourceViewTrackView,
)


router = DefaultRouter()
router.register(r"", ResourceViewSet, basename="resource")

urlpatterns = [
    path("<int:resource_id>/save/", ResourceSaveView.as_view(), name="resource-save"),
    path("<int:resource_id>/upvote/", ResourceUpvoteView.as_view(), name="resource-upvote"),
    path("<int:resource_id>/view/", ResourceViewTrackView.as_view(), name="resource-view-track"),
    path("<int:resource_id>/download/", ResourceDownloadTrackView.as_view(), name="resource-download-track"),
    path("<int:resource_id>/rating/", ResourceRatingView.as_view(), name="resource-rating"),
    *router.urls,
]
