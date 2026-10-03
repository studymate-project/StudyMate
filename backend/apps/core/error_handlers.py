"""API-aware Django error handlers that preserve normal non-API behavior."""

from django.http import JsonResponse
from django.views.csrf import csrf_failure
from django.views.defaults import page_not_found, permission_denied, server_error


def _is_api_request(request) -> bool:
    return request.path_info.startswith("/api/")


def api_csrf_failure(request, reason=""):
    if _is_api_request(request):
        return JsonResponse({"detail": "CSRF verification failed."}, status=403)
    return csrf_failure(request, reason)


def api_permission_denied(request, exception):
    if _is_api_request(request):
        return JsonResponse({"detail": "Permission denied."}, status=403)
    return permission_denied(request, exception)


def api_page_not_found(request, exception):
    if _is_api_request(request):
        return JsonResponse({"detail": "Not found."}, status=404)
    return page_not_found(request, exception)


def api_server_error(request):
    if _is_api_request(request):
        return JsonResponse({"detail": "Internal server error."}, status=500)
    return server_error(request)
