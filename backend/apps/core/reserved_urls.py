"""Authentication routes that are intentionally kept separate from domain APIs."""

from django.urls import path

from .views import (
    CsrfTokenView,
    LoginView,
    LogoutView,
    MeView,
    RefreshView,
    SignupVerificationRequestView,
    SignupVerificationVerifyView,
    SignupView,
)


urlpatterns = [
    path("csrf/", CsrfTokenView.as_view(), name="auth-csrf"),
    path("signup/", SignupView.as_view(), name="auth-signup"),
    path(
        "signup/verification/request/",
        SignupVerificationRequestView.as_view(),
        name="auth-signup-verification-request",
    ),
    path(
        "signup/verification/verify/",
        SignupVerificationVerifyView.as_view(),
        name="auth-signup-verification-verify",
    ),
    path("login/", LoginView.as_view(), name="auth-login"),
    path("me/", MeView.as_view(), name="auth-me"),
    path("refresh/", RefreshView.as_view(), name="auth-refresh"),
    path("logout/", LogoutView.as_view(), name="auth-logout"),
]
