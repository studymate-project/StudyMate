from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import OnboardingView, StudentProfileViewSet


router = DefaultRouter()
router.register(r"", StudentProfileViewSet, basename="user-profile")

urlpatterns = [
    path("onboarding/", OnboardingView.as_view(), name="user-onboarding"),
] + router.urls
