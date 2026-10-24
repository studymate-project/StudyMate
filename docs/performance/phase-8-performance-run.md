# Phase 8 performance-run guide and report template

This guide defines a repeatable local/staging comparison for the existing
StudyMate API. It is a measurement record, not a performance claim. Never use
production URLs, Neon production databases, shared production Redis, real user
accounts/data, or production Celery workers.

The request generator is [`tools/api_load_test.py`](../../tools/api_load_test.py).
It has no dedicated load-test dependency, uses only bounded read-only requests,
and prints its tool version and workload metadata.

## Fixed run contract

Baseline and optimized runs must use the same values for every field below.
Change only the application version or the explicitly documented optimization.
If a field differs, record the runs as non-comparable.

| Field | Baseline | Optimized | Required record |
| --- | --- | --- | --- |
| Environment | `local` or isolated `staging` | same | target and isolation owner |
| Base URL/host | `not yet measured` | `not yet measured` | exact host; no credentials |
| API endpoint/request shape | `not yet measured` | `not yet measured` | path, query, page, page size, auth mode |
| Dataset/fixture snapshot | `not yet measured` | `not yet measured` | fixture version or database snapshot ID |
| Application release/commit | `not yet measured` | `not yet measured` | commit/deployment ID |
| Host/instance shape | `not yet measured` | `not yet measured` | vCPU, memory, instance count if available |
| Tool/version | `not yet measured` | `not yet measured` | harness version and Python version |
| Warm-up | `not yet measured` | `not yet measured` | count, rate, and whether excluded from results |
| Cache state | `cold` or `warm` | same | reset/warm-up procedure and timestamp |
| Concurrency/rate | `not yet measured` | `not yet measured` | `--concurrency`, `--rate` |
| Duration/request cap | `not yet measured` | `not yet measured` | `--duration`, `--max-requests` |
| Repetitions | `not yet measured` | `not yet measured` | same count and run order |
| UTC measurement window | `not yet measured` | `not yet measured` | start/end for every run |

Use synthetic fixtures and the same pre-existing test account for authenticated
reads. Do not create accounts, upload files, send email, trigger interactions,
run retention cleanup, or start Celery Beat. The harness performs no retries.

## Actual supported API shapes

These are the read-only targets currently allowlisted by the harness:

| Label | Request | Auth |
| --- | --- | --- |
| `health` | `GET /api/health/` | anonymous |
| `search` | `GET /api/search/?q=load-test-smoke&limit=5&offset=0` | anonymous |
| `resources` | `GET /api/resources/?page=1&page_size=5` | anonymous |
| `videos` | `GET /api/videos/?page=1&page_size=5` | anonymous |
| `questions` | `GET /api/questions/?page=1&page_size=5` | anonymous |
| `subjects` | `GET /api/resources/subjects/` | bearer test account |
| `notifications` | `GET /api/notifications/?page=1&page_size=5` | bearer test account |
| `profile` | `GET /api/auth/me/` | bearer test account |

Do not substitute a different query, account, page size, or endpoint between
baseline and optimized runs without recording it as a separate workload.

## Repeatable run procedure

1. Provision or select a disposable local/staging PostgreSQL database and,
   where applicable, isolated Redis and Celery services. Verify the API host,
   application release, fixture snapshot, and service shape. Do not echo URLs,
   credentials, cookies, or tokens.
2. Select one cache condition. For `cold`, clear only an isolated cache that
   can be safely discarded; never use `FLUSHALL` on a shared Redis. For `warm`,
   run the same fixed warm-up against the same fixture and exclude those
   requests from the measured output. If the state cannot be reset or verified,
   record it as `unavailable` rather than comparing runs.
3. Run `--dry-run` and save its JSON output as the workload manifest. Use the
   same explicit values for both versions. The harness default is a small smoke
   test; increasing it requires owner approval.
4. Run the fixed warm-up, then the measured workload. Save the JSON output and
   the UTC start/end timestamps. Repeat the same number of times for baseline
   and optimized versions, preferably alternating order when deployment setup
   permits.
5. Collect database, Redis, and Celery observations for the same UTC windows.
   Mark a metric unavailable when the local instrumentation or provider plan
   does not expose it. Do not turn a missing value into zero.
6. Restore or discard the disposable fixture and test services. Remove any
   token environment variable and stop the local API. Do not clean shared or
   production data.

Example smoke commands (placeholders are intentionally not real targets):

```powershell
python tools/api_load_test.py `
  --base-url http://127.0.0.1:8000 `
  --target-environment local `
  --endpoint search `
  --duration 3 `
  --concurrency 1 `
  --rate 1 `
  --max-requests 3 `
  --dry-run `
  --format json

# Fixed warm-up; exclude this output from the measured result.
python tools/api_load_test.py `
  --base-url http://127.0.0.1:8000 `
  --target-environment local `
  --endpoint search `
  --duration 3 `
  --concurrency 1 `
  --rate 1 `
  --max-requests 3 `
  --format json | Tee-Object phase8-warmup.json

# Fixed measured run; use exactly the same command for both versions.
python tools/api_load_test.py `
  --base-url http://127.0.0.1:8000 `
  --target-environment local `
  --endpoint search `
  --duration 10 `
  --concurrency 1 `
  --rate 1 `
  --max-requests 20 `
  --format json | Tee-Object phase8-measured.json
```

The commands above are examples only and were not run as part of this guide.
For staging, also provide `--target-environment staging` and the exact
`--staging-hostname`. For private endpoints, use the documented bearer-token
environment-variable flow; never put a token in the command or report.

## Metric collection and availability

| Metric | Safe collection method | Classification rule |
| --- | --- | --- |
| Request count, errors, timeouts, status codes | Harness JSON output | `measured` when the run completes with saved output |
| Throughput | Harness `throughput_requests_per_second`; retain observed wall time | `measured`, not a capacity claim |
| p50/p95 request latency | Harness JSON output; exclude fixed warm-up | `measured` for the exact workload only |
| SQL queries/request | Local Django `APIClient` plus `CaptureQueriesContext(connection)` against the same fixtures; existing search/subject measurement scripts use this pattern | `measured` only when server-side query capture covers the same request shape; otherwise `unavailable` |
| Slow-query count/details | `SlowQueryLoggingMiddleware` logs duration, route, verb, and operation only above `DB_SLOW_QUERY_THRESHOLD_MS`; inspect redacted local/staging logs | `measured` only for observed log records; it is not total query count |
| DB CPU | Local PostgreSQL host metrics or the approved staging provider dashboard for the same UTC window | `measured` only if the source exposes it; never infer from request latency |
| DB active/peak connections | Local `pg_stat_activity` on the disposable database or approved staging provider dashboard; compare with the configured web/worker shape | `measured` with source and sampling interval; otherwise `unavailable` |
| Redis memory | Isolated Redis/provider dashboard memory metric; do not flush or inspect shared production Redis | `measured` only from the selected isolated/provider source |
| Redis hits/misses | Provider cache statistics, or `python manage.py cache_status --json` for the StudyMate subject-cache namespace when `CACHE_METRICS_ENABLED=True` | Application counters are namespace/day-scoped, not global Redis hit ratio |
| Celery queue delay | Current `python manage.py celery_status --json` reports queue depth and scheduled-task age, but not pending-message enqueue age | `unavailable` as queue delay unless enqueue/start timestamps are available from approved instrumentation |

The repository's slow-query middleware deliberately omits SQL text and
parameters. The Celery status command reports `oldest_pending_task_age` as
unavailable because generic inspection has no enqueue timestamp. Preserve those
limitations in the report.

## Report template

### Run metadata

| Field | Value |
| --- | --- |
| Owner / approval reference | `not yet measured` |
| Baseline commit / optimized commit | `not yet measured` |
| Environment and exact host | `not yet measured` |
| Fixture/database snapshot | `not yet measured` |
| Tool and Python version | `not yet measured` |
| Cache state and reset/warm-up evidence | `not yet measured` |
| Workload manifest path | `not yet measured` |
| UTC run windows | `not yet measured` |
| Notes / deviations | `none recorded` |

### Results

Use `measured`, `estimated`, or `unavailable` in the classification column.
Estimates must include their method and assumptions; do not use estimates as
measured savings.

| Metric | Unit | Baseline | Optimized | Classification | Source / method | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| Requests completed | count | `not yet measured` | `not yet measured` | `unavailable` | harness JSON |  |
| Errors / timeouts | count and % | `not yet measured` | `not yet measured` | `unavailable` | harness JSON |  |
| Throughput | requests/sec | `not yet measured` | `not yet measured` | `unavailable` | harness observed wall time |  |
| p50 latency | ms | `not yet measured` | `not yet measured` | `unavailable` | harness JSON |  |
| p95 latency | ms | `not yet measured` | `not yet measured` | `unavailable` | harness JSON |  |
| SQL queries/request | count | `not yet measured` | `not yet measured` | `unavailable` | Django query capture |  |
| DB CPU | % | `not yet measured` | `not yet measured` | `unavailable` | host/provider dashboard |  |
| DB active/peak connections | count | `not yet measured` | `not yet measured` | `unavailable` | `pg_stat_activity`/provider |  |
| Redis memory | bytes/MB | `not yet measured` | `not yet measured` | `unavailable` | isolated Redis/provider |  |
| Redis hits/misses | count or rate | `not yet measured` | `not yet measured` | `unavailable` | provider or scoped cache counters |  |
| Celery queue delay | ms/sec | `not yet measured` | `not yet measured` | `unavailable` | approved timestamp instrumentation |  |

Do not calculate savings from missing values. If a result is estimated, retain
the raw inputs and assumptions beside it; otherwise leave the comparison
unavailable.

## Owner-approved acceptance thresholds

Thresholds are configuration, not repository claims. An owner must approve the
values and scope before a run. Leave them blank until approved.

| Metric | Direction | Approved threshold | Owner / date | Baseline status | Optimized status |
| --- | --- | --- | --- | --- | --- |
| p95 latency | at most | `not approved` | `not approved` | `not evaluated` | `not evaluated` |
| Error rate | at most | `not approved` | `not approved` | `not evaluated` | `not evaluated` |
| Throughput | at least | `not approved` | `not approved` | `not evaluated` | `not evaluated` |
| SQL queries/request | at most | `not approved` | `not approved` | `not evaluated` | `not evaluated` |
| DB CPU | at most | `not approved` | `not approved` | `not evaluated` | `not evaluated` |
| DB connections | at most | `not approved` | `not approved` | `not evaluated` | `not evaluated` |
| Redis memory | at most | `not approved` | `not approved` | `not evaluated` | `not evaluated` |
| Celery queue delay | at most | `not approved` | `not approved` | `not evaluated` | `not evaluated` |

The repository contains no measured Phase 8 baseline, approved thresholds, or
provider telemetry. This template therefore intentionally reports no savings
or pass/fail result until the owner supplies thresholds and the corresponding
measurements.
