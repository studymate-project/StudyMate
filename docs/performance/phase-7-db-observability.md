# Phase 7 database observability

## Current connection policy

`backend/backend/settings.py` keeps `DB_CONN_MAX_AGE=0` by default and enables
connection health checks. This is intentional for the documented Render web
and worker deployment: the repository does not contain verified Gunicorn
worker/thread counts or the active PostgreSQL/Neon connection capacity. No
persistent-connection change is justified without comparable measurements.

Measure connection pressure only against an isolated/local PostgreSQL database:

- inspect active sessions with `pg_stat_activity`;
- compare peak sessions with the actual web-worker/thread and worker-process
  configuration;
- measure request latency and query counts with a local Django `APIClient`,
  `time.perf_counter()`, and `CaptureQueriesContext(connection)`;
- discard a warm-up request and report fixed-sample median/p95 latency and
  query-count distributions separately by endpoint and page shape.

Never print `DATABASE_URL`, connection credentials, cookies, authorization
headers, or query parameters. Do not run `EXPLAIN ANALYZE` against Neon or any
production database.

## Slow-query logging

`apps.core.db_observability.SlowQueryLoggingMiddleware` uses Django's existing
`connection.execute_wrapper()` API. It logs only queries at or above
`DB_SLOW_QUERY_THRESHOLD_MS` (250 ms by default): duration, database alias, SQL
verb, HTTP method, and resolved route. It never logs SQL text or parameter
values. Production enables it by default; local/debug mode is quiet unless
explicitly enabled.

This is an initial operational threshold, not a measured application latency
claim. Tune it after collecting isolated baseline data and review log volume.
Provider-level slow-query views, connection counts, wait events, and Neon
utilization remain manual dashboard checks because no provider metrics
integration exists in the repository.

## Query changes

No ORM query was changed in this step. Existing resource, search, and community
tests already assert that query counts do not grow with result/event rows.
Notification target serialization contains a possible generic-target query per
notification, but there is no safe comparable measurement in the current test
environment; it should be measured before considering a targeted optimization.
