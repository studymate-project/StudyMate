import logging
from uuid import uuid4

from django.conf import settings
from django.core.cache import cache
from django.db import transaction

from apps.core.cache_metrics import record_cache_event


SUBJECT_CACHE_NAMESPACE = "studymate:subjects"
SUBJECT_CACHE_VERSION = "v1"
SUBJECT_CACHE_GLOBAL_VERSION_KEY = (
    f"{SUBJECT_CACHE_NAMESPACE}:version:{SUBJECT_CACHE_VERSION}:global"
)
SUBJECT_CACHE_USER_VERSION_NAMESPACE = (
    f"{SUBJECT_CACHE_NAMESPACE}:version:{SUBJECT_CACHE_VERSION}:user"
)

logger = logging.getLogger(__name__)


def _read_version(key: str) -> str:
    try:
        value = cache.get(key)
    except Exception:
        logger.warning("Subject cache version read failed", exc_info=True)
        return "0"
    return str(value or "0")


def get_subject_cache_version() -> str:
    return _read_version(SUBJECT_CACHE_GLOBAL_VERSION_KEY)


def get_subject_user_cache_version(user_id: int) -> str:
    return _read_version(f"{SUBJECT_CACHE_USER_VERSION_NAMESPACE}:{user_id}")


def invalidate_subjects_cache(user_id: int | None = None) -> None:
    """Version subject keys after commit; cache failures leave bounded TTL staleness."""
    if user_id is None:
        key = SUBJECT_CACHE_GLOBAL_VERSION_KEY
    else:
        key = f"{SUBJECT_CACHE_USER_VERSION_NAMESPACE}:{user_id}"

    try:
        cache.set(
            key,
            uuid4().hex,
            timeout=settings.SUBJECT_RECOMMENDATION_CACHE_VERSION_TTL_SECONDS,
        )
    except Exception:
        # A successful write must not fail because Redis is unavailable. Existing
        # keys remain usable only until their normal short TTL expires.
        logger.warning("Subject cache invalidation failed", exc_info=True)


def schedule_subjects_cache_invalidation(user_id: int | None = None) -> None:
    transaction.on_commit(lambda: invalidate_subjects_cache(user_id))
