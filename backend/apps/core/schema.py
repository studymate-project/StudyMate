"""OpenAPI extensions for StudyMate's custom authentication."""

from django.conf import settings
from drf_spectacular.extensions import OpenApiAuthenticationExtension
from drf_spectacular.plumbing import build_bearer_security_scheme_object
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, OpenApiTypes


BAD_REQUEST = OpenApiResponse(
    response=OpenApiTypes.OBJECT,
    description="Validation failed; the response contains field-level error details.",
)
UNAUTHENTICATED = OpenApiResponse(
    response=OpenApiTypes.OBJECT,
    description="Authentication is required or the supplied credentials are invalid.",
)
FORBIDDEN = OpenApiResponse(
    response=OpenApiTypes.OBJECT,
    description="The authenticated user is not allowed to perform this operation.",
)
NOT_FOUND = OpenApiResponse(
    response=OpenApiTypes.OBJECT,
    description="The requested object does not exist or is not visible to the caller.",
)
CSRF_HEADER = OpenApiParameter(
    "X-CSRFToken",
    OpenApiTypes.STR,
    OpenApiParameter.HEADER,
    required=True,
    description="Django CSRF token required for unsafe cookie-authenticated requests.",
)


class CookieJWTScheme(OpenApiAuthenticationExtension):
    """Describe the existing Bearer-header and access-cookie auth alternatives."""

    target_class = 'apps.core.authentication.CookieJWTAuthentication'
    name = ['bearerAuth', 'jwtCookieAuth']
    priority = 1

    def get_security_requirement(self, auto_schema):
        return [{'bearerAuth': []}, {'jwtCookieAuth': []}]

    def get_security_definition(self, auto_schema):
        return [
            build_bearer_security_scheme_object(
                header_name='Authorization',
                token_prefix='Bearer',
                bearer_format='JWT',
            ),
            {
                'type': 'apiKey',
                'in': 'cookie',
                'name': settings.JWT_ACCESS_COOKIE_NAME,
                'description': (
                    'HTTP-only access cookie. Unsafe requests authenticated with this cookie '
                    'must also include the CSRF token in the X-CSRFToken header.'
                ),
            },
        ]
