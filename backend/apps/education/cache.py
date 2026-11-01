"""Best-effort caching for public education catalog responses.

Only serialized API payloads are stored here. The catalog endpoints are public
and read-only, so their cache keys do not contain a user identity. A version
component makes invalidation safe for arbitrary list filters without scanning
or clearing the shared Redis database.
"""

import hashlib
import json
import logging
from urllib.parse import urlencode
from uuid import uuid4

from django.conf import settings
from django.core.cache import cache
from django.db import transaction


EDUCATION_CACHE_NAMESPACE = "studymate:education-catalog"
EDUCATION_CACHE_VERSION = "v1"
EDUCATION_CACHE_VERSION_KEY = (
    f"{EDUCATION_CACHE_NAMESPACE}:version:{EDUCATION_CACHE_VERSION}"
)

logger = logging.getLogger(__name__)


def get_education_cache_version() -> str:
    try:
        return str(cache.get(EDUCATION_CACHE_VERSION_KEY) or "0")
    except Exception:
        logger.warning("Education catalog cache version read failed", exc_info=True)
        return "0"


def _request_fingerprint(request, lookup: str | None = None) -> str:
    query_items = [
        (key, value)
        for key in sorted(request.query_params)
        for value in sorted(request.query_params.getlist(key))
    ]
    identity = urlencode(
        [
            ("host", request.get_host()),
            ("scheme", request.scheme),
            ("lookup", lookup or ""),
            *query_items,
        ]
    )
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()


def catalog_cache_key(catalog: str, action: str, request, lookup: str | None = None) -> str:
    fingerprint = _request_fingerprint(request, lookup)
    return (
        f"{EDUCATION_CACHE_NAMESPACE}:{EDUCATION_CACHE_VERSION}:"
        f"version-{get_education_cache_version()}:{catalog}:{action}:{fingerprint}"
    )


def get_cached_catalog_response(key: str):
    try:
        return cache.get(key)
    except Exception:
        logger.warning("Education catalog cache read failed", exc_info=True)
        return None


def set_cached_catalog_response(key: str, payload) -> None:
    try:
        # Round-trip through JSON so Redis receives only API-friendly primitive
        # data rather than DRF Response/QuerySet/model objects.
        serialized_payload = json.loads(json.dumps(payload))
    except (TypeError, ValueError):
        logger.warning("Education catalog response was not cache-serializable")
        return

    try:
        cache.set(
            key,
            serialized_payload,
            timeout=settings.EDUCATION_CATALOG_CACHE_TTL_SECONDS,
        )
    except Exception:
        logger.warning("Education catalog cache write failed", exc_info=True)


def invalidate_education_catalog_cache() -> None:
    """Invalidate all catalog variants after a committed catalog mutation."""

    try:
        cache.set(
            EDUCATION_CACHE_VERSION_KEY,
            uuid4().hex,
            timeout=settings.EDUCATION_CATALOG_CACHE_VERSION_TTL_SECONDS,
        )
    except Exception:
        # Existing entries have a bounded TTL, so a Redis outage cannot break
        # writes or leave stale catalog responses indefinitely.
        logger.warning("Education catalog cache invalidation failed", exc_info=True)


def schedule_education_catalog_invalidation() -> None:
    transaction.on_commit(invalidate_education_catalog_cache)
