from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import VideoRatingView, VideoViewSet


router = DefaultRouter()
router.register(r"", VideoViewSet, basename="video")

urlpatterns = [
    path("<slug:video_slug>/rating/", VideoRatingView.as_view(), name="video-rating"),
    *router.urls,
]
