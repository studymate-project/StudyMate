# Phase 7 cache policy

This document records the application-level cache policy. The repository does
not contain the active Upstash plan, quota, eviction policy, or billing data,
so provider limits must be verified in the hosting dashboard before changing
deployment settings.

## Cache inventory

- Subject recommendation aggregate values use `studymate:subjects:global:*`
  keys and have a configured 5–15 minute effective TTL, including jitter.
- Personalized subject values use `studymate:subjects:user:*` keys containing
  the user and profile versions. They are not shared between users and use the
  same bounded value TTL.
- Subject global/user version keys are retained for at most
  `SUBJECT_RECOMMENDATION_CACHE_VERSION_TTL_SECONDS` (1800 seconds by
  default). Expiring a version key can cause a harmless recomputation; it
  cannot move durable history out of PostgreSQL.
- Signup email rate-limit keys use
  `SIGNUP_OTP_EMAIL_RATE_WINDOW_SECONDS` (3600 seconds by default).
- Django/DRF throttle keys use the configured throttle windows. Their exact
  key names and counts are owned by the framework and are not included in the
  StudyMate subject-cache counters.
- Optional subject-cache counters use four fixed event keys per UTC day and a
  two-day TTL. They count only subject-cache hits, misses, read errors, and
  write errors.

Redis memory usage for cached values is not reported by the application. A
A Python object or JSON byte count would not equal the serialized Redis memory
 footprint, and provider-specific `MEMORY USAGE` support has not been verified.
Provider memory, eviction, command volume, and billing must therefore be
measured in the actual Redis/Upstash dashboard.

## Memory-budget policy

The application does not invent or enforce a Redis memory quota. The operator
must record the actual plan quota and confirm an eviction policy compatible
with disposable cache data before enabling production cache metrics. The
application guardrails are:

1. Cache only derived subject recommendations and rate-limit/throttle state;
   durable events, notifications, and user history remain in PostgreSQL.
2. Keep recommendation values and metric counters on bounded TTLs.
3. Keep personalized keys user-scoped and avoid caching unique low-reuse API
   queries unless measured reuse justifies them.
4. Use `python manage.py cache_status --json` for a capped count of the
   application-owned subject namespace. It never prints keys, values, URLs, or
   credentials.
5. Treat provider memory and eviction alarms as deployment operations. Django
   must not attempt to change provider-level eviction settings.

`CACHE_METRICS_ENABLED` defaults to `False` because every recorded event adds
cache writes. Enable it only after the provider's memory and command budget
has been confirmed. Cache failures remain best effort: subject aggregation
falls back to PostgreSQL and durable records are not affected.
