# StudyMate Phase 0 Baseline

Timestamp: 2026-10-17T04:34:11Z (2026-10-17 10:04:11 IST)

## Repository snapshot

- Commit: `947a5010d8c87616ecf1ac6038e6374ff730e7ab`
- Branch: `main`
- Remote comparison: local `HEAD` matched `origin/main` (`0` ahead, `0` behind).
- Working tree before this report: clean; no staged, modified, or non-ignored untracked files.
- Working tree after this report: this new, uncommitted report only.

## Validation commands

| Area | Command | Exit | Result |
| --- | --- | ---: | --- |
| Frontend | `npm run lint` | 0 | PASS; ESLint completed without diagnostics. |
| Frontend | `npm run build -- --outDir <temporary-directory>` (sandboxed attempt) | 1 | BLOCKED by process permission while loading the installed Tailwind native module. |
| Frontend | `npm run build -- --outDir <temporary-directory>` (controlled retry) | 0 | PASS; Vite transformed 2,050 modules and produced a temporary production build. The repository's existing `frontend/dist` was not overwritten. |
| Backend | `python manage.py check` | 0 | PASS; no system-check issues. |
| Backend | `python manage.py makemigrations --check` | 0 | PASS; no model changes detected. |
| Backend | `python manage.py test` | 1 | FAILED during test-database setup; 299 tests were discovered, but no tests executed. SQLite reported `OperationalError: near "OR": syntax error`. |

The backend test command was run with runtime-only, local-safe overrides: an in-memory SQLite database and local/no-op service configuration. The configured `.env` database and production services were not contacted. No standalone migration, seed, or production command was run; Django's test runner attempted its normal temporary test-database setup before failing.

## Failures and blockers

- The full backend suite cannot currently complete against the safe local SQLite setup because test-database creation reaches SQLite-incompatible migration SQL.
- Running the suite against the configured remote PostgreSQL service was intentionally not attempted because it could alter or depend on a non-local database.
- The first sandboxed frontend build hit a process-permission error loading the installed Tailwind native module; the same build passed on a controlled outside-sandbox retry. No source or dependency changes were made.

## Environment and service dependencies

- Frontend: installed Node/npm dependencies, Vite, React, Tailwind, and ESLint.
- Backend: Python 3.14.3 and the existing backend virtual environment with Django/DRF dependencies.
- Normal backend settings read environment-controlled database, Redis, Celery, email, Cloudinary, and frontend-origin configuration. Secret values and connection details are intentionally omitted.
- No packages were installed and no production credentials or services were used.

## Measurements not yet collected

- Runtime request latency, throughput, error rate, and browser/RUM timings.
- Database query counts, slow-query data, connection usage, and Neon cost/utilization.
- Redis cache hit/miss rates, memory usage, Upstash command volume, and Celery queue/task timings.
- Cloudinary bandwidth/storage usage and hosting cost data.
- Load-test results, production-like traffic profiles, and before/after performance budgets.

## Limitations

This is an inspection and validation baseline only. It does not represent production performance or cost, and the backend application test suite remains incomplete because its isolated local test database could not be created. No application code, dependency manifest, credentials, or Git history was changed.

## API behavior: code-based observations

Source inspected: `backend/backend/urls.py`, `backend/apps/core/urls.py`, `backend/apps/resources/urls.py`, `backend/apps/resources/views.py`, `backend/apps/resources/serializers.py`, `backend/apps/core/search.py`, and the existing API tests.

### `GET /api/resources/subjects/`

- Route: the `ResourceViewSet` detail=False action `subject_recommendations`, mounted through `/api/resources/`.
- Permission: `IsAuthenticated`; unauthenticated requests return `401`. Authentication is supplied by the existing cookie-JWT, bearer-JWT, or session classes. No credentials or cookies were used for this inspection.
- Success: `200` with an unpaginated object containing `results`, `count`, `profile_complete`, and `has_interests`.
- Each result contains `name`, `slug`, `content_count`, `engagement_count`, `recent_engagement_count`, `is_personalized`, and `is_trending`.
- `limit` defaults to 12, is clamped to 1–24, and malformed values fall back to 12; it does not produce a validation error.
- Recommendations aggregate published resources and videos, then apply profile academic-level/interest relevance, engagement, recent activity, and deterministic name tie-breaking. The endpoint performs Python-side ranking after database aggregation.

### `GET /api/resources/` resource list and resource search

- Permission: `AllowAny` for list/retrieve. Anonymous callers see published resources only; authenticated callers also see their own non-published resources. Writes require authentication and owner permission, but are outside this baseline.
- Success: `200` with DRF page-number pagination: `count`, `next`, `previous`, and `results`.
- Default page size is 20; `page_size` is accepted up to 100. Invalid or out-of-range page numbers return `404`.
- Resource result fields are `id`, `title`, `slug`, `description`, `uploader`, `subject`, `topic`, `course`, `semester`, `academic_level`, `resource_type`, `file`, `external_url`, `tags`, `difficulty`, `status`, `created_at`, `updated_at`, `views`, `downloads`, `saves`, `upvotes`, `rating`, `rating_count`, `user_rating`, and `is_saved`.
- Filters: `subject` and `topic` are trimmed, case-insensitive exact matches; `resource_type` and `difficulty` accept stored values or display labels; `academic_level` accepts numeric ID, slug, or name; `uploader` accepts a positive numeric user ID; `tags` may be repeated and matches tag slug/name case-insensitively. Invalid choice/ID filters return an empty result set. Tag filtering uses `distinct()`.
- `search` is trimmed and case-insensitively searches title, subject, topic, course, semester, description, and tag name/slug. Match priority is title, metadata, description, then tags. Without explicit ordering, results sort by that rank, newest `created_at`, then descending primary key.
- Ordering values are `latest`, `popular`, `top_rated`/`top rated`, and `most_downloaded`/`most downloaded`. The default is newest creation time with descending primary-key tie-breaker. Unknown ordering falls back to the default ordering.

### `GET /api/search/` unified search

- Permission: `AllowAny`; successful requests return `200`.
- Query validation: required non-blank `q`, maximum length 200; whitespace is normalized and null characters are rejected. `limit` defaults to 20 and is bounded 1–50. `offset` defaults to 0 and is bounded 0–1000. Invalid input returns `400`.
- Response shape: `query`, `results`, `limit`, `offset`, `has_more`, and nullable `next_offset`.
- Each result contains `type`, `id`, `title`, `snippet`, `metadata`, `detail_url`, and `score`. Resource, video, question, and public-user results are combined and globally ranked. Anonymous visibility is published content and active public users; authenticated callers additionally see their own non-published content.
- Resource/video/question search uses PostgreSQL full-text ranking plus trigram similarity. Candidate rows are bounded per content type, then combined and sorted by score, creation/join date, type, and ID. This endpoint is not SQLite-compatible because it executes PostgreSQL-specific search SQL and `pg_trgm` configuration.

## Safe measurement method and availability

The safe repeatable method is a Django test or local-only harness using `APIClient`, representative fixture data, `time.perf_counter()` around the request, and `CaptureQueriesContext(connection)` around the same request. Use `force_authenticate()` for the private subjects endpoint so no cookies or authorization headers are logged. Discard a warm-up request, then repeat a fixed number of samples against the same fixture snapshot and report sample count, median/p95 latency, and query-count distribution separately for each endpoint/request shape. Existing subject-recommendation and resource-search tests provide representative fixture patterns.

No endpoint measurements were collected in this phase (sample count: 0). The local PostgreSQL 18 service is running, but loopback authentication requires an unavailable local password. The safe SQLite attempt cannot create the test database because PostgreSQL-specific migration/search SQL fails on SQLite. The configured `.env` database was not used, and no production or remote service was contacted.

Safest later setup: provide a disposable loopback-only PostgreSQL database through an untracked local environment setting, verify it with `pg_isready`, then run targeted Django tests or a temporary measurement harness with `DATABASE_URL` pointed only at that local database. Do not echo the setting, credentials, cookies, authorization headers, or query values. No application code or API behavior was changed during this inspection.

## Configuration inspection

Inspected `backend/backend/settings.py`, `backend/backend/celery.py`, `backend/apps/users/tasks.py`, the verification service, `backend/start.sh`, `backend/worker.sh`, `backend/README.md`, `frontend/package.json`, `frontend/vite.config.js`, `frontend/vercel.json`, and both environment templates. Values from local environment files and deployment credentials were not read or recorded.

### Redis and cache

Confirmed:

- `REDIS_URL` selects `django_redis.cache.RedisCache`; production requires the `rediss` TLS scheme. If production has no `REDIS_URL`, settings fail during startup. Debug/local mode falls back to Django `LocMemCache`.
- The cache configuration has no application-defined global `TIMEOUT`, key prefix, socket timeout, connection pool, or retry/failure options. Known cache entries use explicit call-site behavior: signup email rate limiting uses `SIGNUP_OTP_EMAIL_RATE_WINDOW_SECONDS` (default 3600 seconds); OTP expiry and resend cooldown are database/model timing controls, not cache TTLs.
- Redis is used by Django/DRF throttling and signup-email rate limiting. No general response/page caching was found in the inspected application code.
- The rate limiter fails closed for `ValueError` from cache increment. There is no broader application-level Redis exception policy; other runtime behavior is delegated to the configured cache backend.

Inferred or unavailable:

- The repository documents Upstash as the intended Redis provider, but the active provider, reachability, latency, memory usage, eviction behavior, and failure behavior were not runtime-verified.
- No live Redis integration test was run. The existing test is conditional on `REDIS_URL` being configured and would perform a Redis round trip.

### Celery

Confirmed:

- `CELERY_BROKER_URL` is dedicated but falls back to `REDIS_URL`; accepted schemes are `redis` and `rediss`, with production requiring `rediss` and certificate verification enabled.
- Celery is configured from Django settings with the `CELERY_` namespace. JSON is the only accepted task format, task results are ignored, broker startup retry is enabled, and worker prefetch is `1`.
- Task discovery is explicitly limited to `apps.users`; the repository currently contains one task module, `apps/users/tasks.py`.
- Signup email delivery is a separate task with late acknowledgements, result ignoring, automatic retry for any exception, backoff enabled, and a maximum of three retries. Dispatch occurs after transaction commit; broker dispatch failure is surfaced rather than reported as a successful signup.
- `worker.sh` starts `python -m celery -A backend.celery worker` with configurable log level and hostname. No explicit queue routing, queue declarations, concurrency, task time limit, result backend, or worker recycling settings were found; those behaviors therefore remain Celery defaults unless supplied externally.

Inferred or unavailable:

- The worker is intended as a separate long-lived deployment process, but worker health, queue depth, retry timing, and broker connectivity were not runtime-verified.

### Django database and PostgreSQL provider

Confirmed:

- `DATABASE_URL` is required by `env.db`; there is no application SQLite fallback. Non-debug settings reject non-PostgreSQL engines.
- `DB_SSLMODE` defaults to a TLS-required mode in production and is applied explicitly so a conflicting URL option cannot weaken the production requirement.
- `DB_CONN_MAX_AGE` defaults to `0` and `DB_CONN_HEALTH_CHECKS` defaults to enabled. This is a no-pooling-by-default configuration; connection reuse is opt-in through environment configuration.
- The backend depends on `psycopg2-binary`. Startup applies committed migrations before Gunicorn serves requests.

Inferred or unavailable:

- The repository confirms PostgreSQL configuration and documents the hosted PostgreSQL deployment, but the active Neon database/provider endpoint, connection capacity, query latency, and runtime TLS state were not verified because the connection setting was not read or used.

### Deployment and health checks

Confirmed:

- `backend/start.sh` runs `python manage.py migrate --noinput`, then starts Gunicorn on `0.0.0.0:${PORT:-8000}` with access and error logs sent to stdout/stderr.
- `backend/worker.sh` is a separate process entrypoint; the web process does not run Celery workers.
- `GET /api/health/` is public and returns `200` with `{"status":"ok"}`. It is a process-level health check only: the view does not probe PostgreSQL, Redis, Celery, email, or Cloudinary.
- The backend README documents Render web and background-worker services, PostgreSQL, Upstash Redis, Cloudinary, and the health-check path. The frontend Vercel configuration rewrites all routes to `index.html`; Vite provides a development-only `/api` proxy to the local backend. Frontend scripts provide `dev`, `build`, `lint`, and `preview`.

Required environment variable names are present in code/documentation for database, Redis, Celery broker, email, Cloudinary, origins, JWT, security, logging, throttling, and deployment port settings. The backend `.env.example` does not enumerate every operational variable documented as required for deployment, notably Redis/Celery broker and SMTP settings. This is a configuration-documentation risk, not proof that deployment values are missing.

### Configuration risks and blockers

- Web startup is coupled to migration completion, so migration time or failure directly affects deployment readiness.
- The shallow health endpoint can remain green while database, Redis, broker, email, or Cloudinary dependencies are unavailable.
- Redis cache and Celery broker share one fallback setting, which couples their provider availability and resource usage unless a separate broker is configured.
- Missing explicit Redis client timeouts/retry policy, Celery queue routing/time limits, and cache-wide TTL policy leave important runtime behavior to library/provider defaults.
- Actual production configuration and provider health remain unavailable without reading credentials or connecting to external services; no such access was attempted.
