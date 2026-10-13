from django.conf import settings
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from drf_spectacular.utils import OpenApiParameter, OpenApiTypes, extend_schema, extend_schema_view, inline_serializer
from rest_framework import serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.generics import CreateAPIView
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import RefreshToken

from apps.users.serializers import (
    LoginSerializer,
    PublicUserSerializer,
    RegistrationSerializer,
    StudentProfileSerializer,
)

from .authentication import CookieJWTAuthentication
from .schema import BAD_REQUEST, CSRF_HEADER, FORBIDDEN, NOT_FOUND, UNAUTHENTICATED
from .search import SearchRequestSerializer, SearchResponseSerializer, normalize_search_query, search_content


AUTH_USER_DATA = inline_serializer(
    "AuthUserData",
    fields={
        "id": serializers.IntegerField(read_only=True),
        "username": serializers.CharField(read_only=True),
        "first_name": serializers.CharField(read_only=True),
        "last_name": serializers.CharField(read_only=True),
        "email": serializers.EmailField(read_only=True),
        "profile": StudentProfileSerializer(required=False),
    },
)
AUTH_RESPONSE = inline_serializer(
    "AuthResponse",
    fields={
        "detail": serializers.CharField(read_only=True),
        "user": AUTH_USER_DATA,
    },
)
ME_RESPONSE = inline_serializer(
    "MeResponse",
    fields={"user": AUTH_USER_DATA},
)
REGISTRATION_RESPONSE = inline_serializer(
    "RegistrationResponse",
    fields={
        "user": AUTH_USER_DATA,
        "profile": StudentProfileSerializer(read_only=True),
    },
)
REFRESH_RESPONSE = inline_serializer(
    "RefreshResponse",
    fields={"detail": serializers.CharField(read_only=True)},
)
ROOT_RESPONSE = inline_serializer(
    "ApiRootResponse",
    fields={
        "service": serializers.CharField(read_only=True),
        "status": serializers.CharField(read_only=True),
        "namespaces": serializers.DictField(read_only=True),
    },
)
HEALTH_RESPONSE = inline_serializer(
    "HealthResponse",
    fields={"status": serializers.CharField(read_only=True)},
)
CSRF_RESPONSE = inline_serializer(
    "CsrfResponse",
    fields={"csrf_token": serializers.CharField(read_only=True)},
)


def enforce_cookie_csrf(request):
    """Enforce CSRF for browser API mutations while honoring DRF test clients."""

    if getattr(request._request, "_dont_enforce_csrf_checks", False):
        return
    SessionAuthentication().enforce_csrf(request)


@extend_schema_view(
    post=extend_schema(
        summary="Create an account",
        description="Create a user and initial profile with identity and optional location data. Education selections are completed during onboarding.",
        request=RegistrationSerializer,
        responses={201: REGISTRATION_RESPONSE, 400: BAD_REQUEST},
    )
)
class SignupView(CreateAPIView):
    """Public account creation endpoint; token issuance is handled later."""

    serializer_class = RegistrationSerializer
    permission_classes = (AllowAny,)
    throttle_scope = "auth_signup"

    def post(self, request, *args, **kwargs):
        enforce_cookie_csrf(request)
        return super().post(request, *args, **kwargs)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CsrfTokenView(APIView):
    """Issue Django's CSRF cookie and token for browser API clients."""

    authentication_classes = ()
    permission_classes = (AllowAny,)

    @extend_schema(
        summary="Get a CSRF token",
        responses={200: CSRF_RESPONSE},
    )
    def get(self, request: Request) -> Response:
        # The cookie is still set for Django's double-submit validation. The
        # response body also carries the non-secret token because a browser
        # hosted on a different origin cannot read a cookie scoped to the API
        # host (for example, Vercel cannot read a Render cookie).
        return Response({"csrf_token": get_token(request)})


class LoginView(APIView):
    """Authenticate by email and place JWTs in secure HTTP-only cookies."""

    permission_classes = (AllowAny,)
    throttle_scope = "auth_login"

    @staticmethod
    def _set_cookie(response, *, name, value, max_age, path, httponly):
        response.set_cookie(
            name,
            str(value),
            max_age=max_age,
            httponly=httponly,
            secure=settings.JWT_COOKIE_SECURE,
            samesite=settings.JWT_COOKIE_SAMESITE,
            path=path,
            domain=settings.JWT_COOKIE_DOMAIN,
        )

    @extend_schema(
        summary="Log in",
        description="Validate email credentials and set HTTP-only access and refresh cookies.",
        request=LoginSerializer,
        responses={200: AUTH_RESPONSE, 400: BAD_REQUEST, 401: UNAUTHENTICATED},
    )
    def post(self, request: Request) -> Response:
        enforce_cookie_csrf(request)
        serializer = LoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        refresh = RefreshToken.for_user(user)
        access = refresh.access_token

        response = Response(
            {
                "detail": "Login successful.",
                "user": safe_user_data(user),
            }
        )
        self._set_cookie(
            response,
            name=settings.JWT_ACCESS_COOKIE_NAME,
            value=access,
            max_age=int(settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"].total_seconds()),
            path=settings.JWT_ACCESS_COOKIE_PATH,
            httponly=settings.JWT_ACCESS_COOKIE_HTTPONLY,
        )
        self._set_cookie(
            response,
            name=settings.JWT_REFRESH_COOKIE_NAME,
            value=refresh,
            max_age=int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds()),
            path=settings.JWT_REFRESH_COOKIE_PATH,
            httponly=settings.JWT_REFRESH_COOKIE_HTTPONLY,
        )
        return response


def safe_user_data(user):
    """Return the shared safe user/profile representation for auth responses."""

    user_data = PublicUserSerializer(user).data
    user_data["email"] = user.email
    profile = getattr(user, "student_profile", None)
    if profile is not None:
        user_data["profile"] = StudentProfileSerializer(profile).data
    return user_data


class MeView(APIView):
    """Return the authenticated user derived from the JWT access cookie."""

    authentication_classes = (CookieJWTAuthentication,)
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        summary="Get the authenticated user",
        responses={200: ME_RESPONSE, 401: UNAUTHENTICATED},
    )
    def get(self, request: Request) -> Response:
        return Response({"user": safe_user_data(request.user)})


class RefreshView(APIView):
    """Refresh the access cookie from the HTTP-only refresh cookie."""

    authentication_classes = ()
    permission_classes = (AllowAny,)
    throttle_scope = "auth_refresh"

    @staticmethod
    def _set_cookie(response, *, name, value, max_age, path, httponly):
        response.set_cookie(
            name,
            str(value),
            max_age=max_age,
            httponly=httponly,
            secure=settings.JWT_COOKIE_SECURE,
            samesite=settings.JWT_COOKIE_SAMESITE,
            path=path,
            domain=settings.JWT_COOKIE_DOMAIN,
        )

    @extend_schema(
        summary="Refresh the access cookie",
        description="Refresh uses the existing HTTP-only refresh cookie and requires CSRF validation.",
        parameters=[CSRF_HEADER],
        request=None,
        responses={200: REFRESH_RESPONSE, 401: UNAUTHENTICATED, 403: FORBIDDEN},
    )
    def post(self, request: Request) -> Response:
        enforce_cookie_csrf(request)
        raw_refresh = request.COOKIES.get(settings.JWT_REFRESH_COOKIE_NAME)
        if not raw_refresh:
            return Response({"detail": "Invalid or expired refresh token."}, status=401)

        serializer = TokenRefreshSerializer(data={"refresh": raw_refresh})
        try:
            is_valid = serializer.is_valid()
        except TokenError:
            return Response({"detail": "Invalid or expired refresh token."}, status=401)
        if not is_valid:
            return Response({"detail": "Invalid or expired refresh token."}, status=401)

        token_data = serializer.validated_data
        response = Response({"detail": "Token refreshed."})
        self._set_cookie(
            response,
            name=settings.JWT_ACCESS_COOKIE_NAME,
            value=token_data["access"],
            max_age=int(api_settings.ACCESS_TOKEN_LIFETIME.total_seconds()),
            path=settings.JWT_ACCESS_COOKIE_PATH,
            httponly=settings.JWT_ACCESS_COOKIE_HTTPONLY,
        )
        if "refresh" in token_data:
            self._set_cookie(
                response,
                name=settings.JWT_REFRESH_COOKIE_NAME,
                value=token_data["refresh"],
                max_age=int(api_settings.REFRESH_TOKEN_LIFETIME.total_seconds()),
                path=settings.JWT_REFRESH_COOKIE_PATH,
                httponly=settings.JWT_REFRESH_COOKIE_HTTPONLY,
            )
        return response


class LogoutView(APIView):
    """Clear auth cookies and blacklist the refresh token when configured."""

    authentication_classes = ()
    permission_classes = (AllowAny,)

    @staticmethod
    def _blacklist_refresh_token(raw_refresh):
        if not raw_refresh or "rest_framework_simplejwt.token_blacklist" not in settings.INSTALLED_APPS:
            return
        try:
            RefreshToken(raw_refresh).blacklist()
        except (AttributeError, TokenError):
            # Logout remains idempotent for missing, malformed, or expired tokens.
            return

    @extend_schema(
        summary="Log out",
        description="Clear the existing access and refresh cookies after CSRF validation.",
        parameters=[CSRF_HEADER],
        request=None,
        responses={204: None, 403: FORBIDDEN},
    )
    def post(self, request: Request) -> Response:
        enforce_cookie_csrf(request)
        self._blacklist_refresh_token(request.COOKIES.get(settings.JWT_REFRESH_COOKIE_NAME))

        response = Response(status=204)
        response.delete_cookie(
            settings.JWT_ACCESS_COOKIE_NAME,
            path=settings.JWT_ACCESS_COOKIE_PATH,
            domain=settings.JWT_COOKIE_DOMAIN,
            samesite=settings.JWT_COOKIE_SAMESITE,
        )
        response.delete_cookie(
            settings.JWT_REFRESH_COOKIE_NAME,
            path=settings.JWT_REFRESH_COOKIE_PATH,
            domain=settings.JWT_COOKIE_DOMAIN,
            samesite=settings.JWT_COOKIE_SAMESITE,
        )
        return response


@extend_schema(
    summary="Get API namespaces",
    responses={200: ROOT_RESPONSE},
)
@api_view(["GET"])
@permission_classes([AllowAny])
def api_root(request: Request) -> Response:
    """Return the available API namespaces without exposing feature routes."""
    return Response(
        {
            "service": "studymate-api",
            "status": "ok",
            "namespaces": {
                "auth": "/api/auth/",
                "users": "/api/users/",
                "education": "/api/education/",
                "resources": "/api/resources/",
                "videos": "/api/videos/",
                "questions": "/api/questions/",
                "notifications": "/api/notifications/",
                "search": "/api/search/",
            },
        }
    )


@extend_schema(
    summary="Check API health",
    responses={200: HEALTH_RESPONSE},
)
@api_view(["GET"])
@permission_classes([AllowAny])
def health(request: Request) -> Response:
    """Return a minimal public status response for deployment checks."""
    return Response({'status': 'ok'})


@extend_schema(
    summary="Search public and accessible study content",
    description=(
        "Search resources, videos, questions, and public users with PostgreSQL full-text and trigram ranking. "
        "Results are bounded and ordered deterministically. Authenticated owners may also find "
        "their own non-published content."
    ),
    parameters=[
        OpenApiParameter(
            "q",
            OpenApiTypes.STR,
            OpenApiParameter.QUERY,
            required=True,
            description="Search terms; whitespace is normalized and limited to 200 characters.",
        ),
        OpenApiParameter(
            "limit",
            OpenApiTypes.INT,
            OpenApiParameter.QUERY,
            required=False,
            default=20,
            description="Number of results to return, from 1 to 50.",
        ),
        OpenApiParameter(
            "offset",
            OpenApiTypes.INT,
            OpenApiParameter.QUERY,
            required=False,
            default=0,
            description="Number of globally ranked results to skip, up to 1000.",
        ),
    ],
    responses={200: SearchResponseSerializer, 400: BAD_REQUEST},
)
class SearchView(APIView):
    permission_classes = (AllowAny,)

    def get(self, request: Request) -> Response:
        request_serializer = SearchRequestSerializer(data=request.query_params)
        request_serializer.is_valid(raise_exception=True)
        query = normalize_search_query(request_serializer.validated_data["q"])
        if not query:
            raise serializers.ValidationError({"q": "Search query must not be blank."})

        return Response(
            search_content(
                request,
                query,
                request_serializer.validated_data["limit"],
                request_serializer.validated_data["offset"],
            )
        )
