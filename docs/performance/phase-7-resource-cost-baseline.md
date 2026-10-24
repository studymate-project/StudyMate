# StudyMate resource and cost baseline

This is a measurement template, not a billing report. The repository documents
Render web and background-worker services, Neon/PostgreSQL, and Upstash Redis,
but it does not contain the active provider plans, account telemetry, prices,
or billing data. Values below are therefore either repository-derived facts or
`not yet measured`.

Do not record connection URLs, passwords, tokens, cookies, authorization
headers, or raw SQL parameters in this document. Use one fixed UTC date range,
the same representative local/test fixture, and the same endpoint/request
shapes for before/after comparisons.

## Collection record

| Field | Value |
| --- | --- |
| Measurement owner/date | `not yet measured` |
| UTC date range | `not yet measured` |
| Release/commit | `not yet measured` |
| Source dashboards/tools | `not yet measured` |
| Environment | `local/test` or `production dashboard` |
| Provider plan names | `not yet measured` |
| Notes about traffic or fixture data | `not yet measured` |

## Repository-derived application facts

| Area | Confirmed baseline | Current measured value |
| --- | --- | --- |
| API pagination | `StudyMatePagination` defaults to 20 items and caps `page_size` at 100 in `backend/apps/core/pagination.py`. | `not yet measured` |
| Database connections | `DB_CONN_MAX_AGE` defaults to 0 and health checks default to enabled in `backend/backend/settings.py`. | `not yet measured` |
| Slow-query logging | `apps.core.db_observability.SlowQueryLoggingMiddleware` logs metadata only at or above `DB_SLOW_QUERY_THRESHOLD_MS` (250 ms default); SQL text and parameters are excluded. | `not yet measured` |
| Subject cache | Global and user-scoped recommendation keys use a bounded 5–15 minute effective TTL; version keys default to 1,800 seconds. | `not yet measured` |
| Signup rate limiting | The configured email rate window defaults to 3,600 seconds. | `not yet measured` |
| Cache counters | Optional UTC-day hit, miss, read-error, and write-error counters have a two-day TTL and are disabled by default. | `not yet measured` |
| Cache diagnostics | `python manage.py cache_status --json` reports a capped subject-key count and current counters without printing keys, values, or credentials. | `not yet measured` |
| Frontend list requests | Resource/question/notification list caches use 30-second client TTLs; catalog data uses a 5-minute TTL. | `not yet measured` |
| Frontend test request count | Isolated mocked video-list concurrency test confirms two concurrent equivalent requests coalesce to one API call. | 1 call for 2 concurrent equivalent requests |

The last row is a unit-test result, not a production request-rate estimate.
No representative API payload-byte or end-to-end latency baseline is stored in
the repository.

## Render collection checklist

Collect the web service and worker service separately. The repository's
documented hosting platform is Render; the committed commands are `sh
start.sh` for the web service and `sh worker.sh` for the background worker,
with service root `backend` as documented in `backend/README.md`.

In each Render service:

1. **Settings / Compute**: record instance type, vCPU, RAM, instance count,
   autoscaling bounds/targets if enabled, and the displayed service price or
   included usage unit. Record the plan name exactly as shown; do not infer it
   from CPU or RAM.
2. **Metrics / Application Metrics**: for the fixed UTC range record CPU
   utilization, memory usage, and peak/median values where the dashboard
   provides them.
3. **Metrics / Network Metrics** (web only): record total HTTP requests,
   status-code breakdown, response-time percentiles if available, and
   outbound bandwidth. A worker normally has no public HTTP request metric;
   record that as `not applicable`, not zero.
4. **Events and Logs**: count instance restarts, deploy failures, health-check
   failures, OOM events, and worker process exits. Record the time window and
   a short redacted cause category, never credentials or task arguments.
5. **Workspace Billing / Usage / Invoices**: record accrued usage, included
   units, overage, and invoice total for the same range. If the plan does not
   expose a metric, record `not available on current plan`.

| Render service | Plan / vCPU / RAM | Instances | Requests | p50/p95 latency | CPU peak | RAM peak | Restarts | Bandwidth | Usage/cost | Source/range |
| --- | --- | ---: | ---: | --- | --- | --- | ---: | --- | --- | --- |
| Web | `not yet measured` | `not yet measured` | `not yet measured` | `not yet measured` | `not yet measured` | `not yet measured` | `not yet measured` | `not yet measured` | `not yet measured` | `not yet measured` |
| Worker | `not yet measured` | `not yet measured` | `not applicable` | `not applicable` | `not yet measured` | `not yet measured` | `not yet measured` | `not yet measured` | `not yet measured` | `not yet measured` |

Render's public documentation describes CPU/memory, web request volume and
latency, outbound bandwidth, and Events history as dashboard measurements.
Availability and retention depend on the workspace/service plan, so the
actual dashboard must be treated as authoritative.

## Neon collection checklist

In the Neon Console, select the actual StudyMate project and production branch,
then record the active plan and compute configuration before taking metrics.
In **Monitoring**, collect compute usage (CPU/RAM), active connections and
connection limit, database/storage size, cache hit ratio where shown, and any
available query/latency or lock/deadlock views. In the **Query performance** or
equivalent query view, record top statements by calls, average time, total time,
and slow-query count/threshold if exposed. Use statement names or redacted
fingerprints; do not copy SQL containing user data or parameters.

In the Neon account/project **Usage or Billing/Consumption** view, record
compute usage, storage, transfer if shown, included allowances, and billed
amount for the same UTC range. The exact metrics and history depend on the
current Neon plan; the repository does not identify that plan.

| Neon metric | Unit | Baseline | Post-optimization | Dashboard/source | Range |
| --- | --- | --- | --- | --- | --- |
| Compute usage | plan-defined unit | `not yet measured` | `not yet measured` | `not yet measured` | `not yet measured` |
| Peak/average CPU | % | `not yet measured` | `not yet measured` | `not yet measured` | `not yet measured` |
| Peak/average RAM | MB or % | `not yet measured` | `not yet measured` | `not yet measured` | `not yet measured` |
| Active connections | count | `not yet measured` | `not yet measured` | `not yet measured` | `not yet measured` |
| Connection limit | count | `not yet measured` | `not yet measured` | `not yet measured` | `not yet measured` |
| Database/storage size | bytes | `not yet measured` | `not yet measured` | `not yet measured` | `not yet measured` |
| Cache hit ratio | % | `not yet measured` | `not yet measured` | `not yet measured` | `not yet measured` |
| Slow/top-query rate | calls, ms | `not yet measured` | `not yet measured` | `not yet measured` | `not yet measured` |
| Compute/storage/transfer cost | plan currency/unit | `not yet measured` | `not yet measured` | `not yet measured` | `not yet measured` |

The application-side slow-query log can be sampled from the Render logs using
its duration, route, verb, and database alias fields. It does not provide a
provider-wide slow-query count. `DB_CONN_MAX_AGE=0` is intentionally unchanged;
do not infer a connection-pooling benefit without comparing connection and
latency measurements.

## Upstash Redis collection checklist

In the Upstash Console, select the actual Redis database and record its plan,
region, configured data-size limit, and eviction setting under the database
details/configuration area. In **Usage/Metrics**, collect memory/data size,
key count, request/command volume, top commands, throughput, p50/p99 service
latency, connections, cache hits/misses, and evictions if exposed. In the
database **Billing/Current month** view, record the displayed request usage,
storage usage, included allowance, and cost. Do not assume a plan limit or
eviction policy from this repository.

| Upstash metric | Unit | Baseline | Post-optimization | Dashboard/source | Range |
| --- | --- | --- | --- | --- | --- |
| Plan and data-size limit | plan-defined | `not yet measured` | `not yet measured` | `not yet measured` | `not yet measured` |
| Data/memory size | bytes | `not yet measured` | `not yet measured` | `not yet measured` | `not yet measured` |
| Key count | count | `not yet measured` | `not yet measured` | `not yet measured` | `not yet measured` |
| Requests/commands | count | `not yet measured` | `not yet measured` | `not yet measured` | `not yet measured` |
| Top commands | count by command | `not yet measured` | `not yet measured` | `not yet measured` | `not yet measured` |
| Throughput | commands/sec | `not yet measured` | `not yet measured` | `not yet measured` | `not yet measured` |
| Service latency | p50/p99 ms | `not yet measured` | `not yet measured` | `not yet measured` | `not yet measured` |
| Connections | count | `not yet measured` | `not yet measured` | `not yet measured` | `not yet measured` |
| Cache hits/misses | count or rate | `not yet measured` | `not yet measured` | `not yet measured` | `not yet measured` |
| Evictions/rejected writes | count | `not yet measured` | `not yet measured` | `not yet measured` | `not yet measured` |
| Requests/storage cost | plan currency/unit | `not yet measured` | `not yet measured` | `not yet measured` | `not yet measured` |

Application counters, when `CACHE_METRICS_ENABLED=True`, cover only the
StudyMate subject-cache namespace. Run `python manage.py cache_status --json`
from an approved service environment and record only aggregate counts. They do
not measure provider-wide memory, all Redis commands, evictions, or billing.
Cache failures remain best effort and subject recommendations fall back to
PostgreSQL; durable records are not stored only in Redis.

## Application measurement protocol

Use an isolated/local PostgreSQL and Redis-compatible test setup, a fixed
fixture snapshot, and a fixed sample count. Never use production connection
strings or send SMTP/email during this exercise.

For each representative endpoint (for example resource list, search, profile,
notifications, and a detail endpoint), record:

- request shape, authenticated/anonymous state, page and `page_size`;
- warm-up count, sample count, median and p95 latency in milliseconds;
- response status and serialized response bytes (`len(response.content)`),
  separately for metadata and result pages where applicable;
- database query count and slow-query log count;
- frontend browser request count by route, including repeated requests during
  navigation, refresh, and authentication restore.

For cache behavior, record subject-cache hits, misses, read errors, and write
errors from the command output, then compute `hits / (hits + misses)` only when
both counters cover the same UTC day and namespace. Do not call it a global
Redis hit ratio.

| Endpoint/request shape | Auth state | Page size | Samples | p50 ms | p95 ms | Response bytes p50/p95 | Queries | Frontend calls | Cache metric source |
| --- | --- | ---: | ---: | --- | --- | --- | --- | --- | --- |
| `not yet measured` | `not yet measured` | `not yet measured` | `not yet measured` | `not yet measured` | `not yet measured` | `not yet measured` | `not yet measured` | `not yet measured` | `not yet measured` |

No comparable representative production payload-size, end-to-end latency,
cache-ratio, or browser request-count baseline is currently present in the
repository. Existing isolated frontend tests prove request coalescing only;
they are not workload measurements.

## Current status and decision rule

Measurable now from repository inspection: configuration defaults, cache TTLs,
pagination bounds, available safe diagnostic commands, and the isolated test
request-count result above. Pending manual collection: all Render instance and
usage/cost values, Neon compute/storage/connections/query metrics, Upstash
memory/commands/evictions/billing, and representative application latency and
payload measurements.

Do not recommend a larger instance, paid monitoring product, connection-pool
change, or VPS migration until the same-range baseline and post-optimization
measurements show a material bottleneck or cost issue.

## Public provider references

- [Render service metrics](https://render.com/docs/service-metrics) and
  [Render compute plans](https://render.com/docs/compute-plans)
- [Neon compute and monitoring guidance](https://neon.com/docs/manage/endpoints/)
  and [Neon plan monitoring](https://neon.com/docs/introduction/plans)
- [Upstash metrics and charts](https://upstash.com/docs/redis/howto/metrics-and-charts)
  and [Upstash eviction](https://upstash.com/docs/redis/features/eviction)
