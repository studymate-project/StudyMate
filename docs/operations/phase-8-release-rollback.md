# Phase 8 production release and rollback runbook

This runbook reflects the repository configuration inspected on 2026-10-24.
The documented hosts are Render for the Django web service and separate Celery
worker, and Vercel for the frontend. No deployment, migration, DNS change,
secret change, Beat process, retention cleanup, or rollback was performed.

## Verified deployment shape

| Component | Repository configuration | Host-specific status |
| --- | --- | --- |
| Backend web | Render root `backend`; build installs `requirements/base.txt` and runs `collectstatic`; start command `sh start.sh` | Render service ID, deploy hook, instance shape, and dashboard permissions are not in the repository |
| Backend worker | Separate Render Background Worker; start command `sh worker.sh`; no migrations in worker entrypoint | Worker count, autoscaling, and dashboard controls are unavailable here |
| Frontend | Vercel project with a catch-all rewrite in `frontend/vercel.json`; `VITE_API_BASE_URL` points to the API | Vercel project/deployment identifiers and rollback permissions are unavailable here |
| Controlled rollout | No canary, blue/green, traffic split, or multi-service routing configuration is committed | Unavailable; do not call a normal Render deploy a canary |
| CI/CD | No checked-in CI workflow or deployment manifest was found | Release approval and provider deployment action are manual/host-specific |

`start.sh` runs `python manage.py migrate --noinput` and starts Gunicorn only
if migrations succeed. `worker.sh` starts Celery separately and does not run
migrations. Deploy the web service before the worker, as documented by the
repository.

## Pre-release gates

Run these checks in a clean checkout or reviewed release candidate. Database
tests require an explicitly disposable local/staging PostgreSQL database;
SQLite is not a substitute because the repository contains PostgreSQL-only
migrations such as `resources.0007_search_indexes` and
`community.0005_search_indexes`.

Backend:

```powershell
cd backend
python manage.py check
python manage.py check --deploy
python manage.py makemigrations --check
python manage.py migrate --plan
python manage.py test <focused-or-full-suite>
```

Use `migrate --plan` and database tests only against the approved disposable
or staging target. Do not run these commands against production during the
pre-release gate. The current test environment has previously been blocked by
SQLite test-database setup; do not bypass that by changing migrations.

Frontend and build parity:

```powershell
cd frontend
npm ci
npm test
npm run lint
npm run build
```

The Render web build command is the repository-documented equivalent of:

```text
pip install -r requirements/base.txt && python manage.py collectstatic --noinput
```

Record command results, commit/release identifier, dependency lockfile state,
and any blocked PostgreSQL/Redis tests. Do not claim a release is ready when a
required gate is unavailable.

## Migration compatibility review

Before approval, review the migration plan and the SQL for every pending
migration. Pay particular attention to:

- `resources.0007_search_indexes` and `community.0005_search_indexes`, which
  require PostgreSQL, `pg_trgm`, PL/pgSQL functions/triggers, data backfills,
  and `CREATE INDEX CONCURRENTLY` in non-atomic migrations.
- `community.0006_discussion_comments`, which creates tables and constraints
  after the search-index migration.
- `users.0007_signupemailverification_email_sent_at` and
  `notifications.0003_notification_recipient_created_idx`, which are additive
  schema/index changes but still require the database to be reachable.

The web startup is coupled to migration completion. A failed or unexpectedly
long migration can prevent the new web process from serving. Prefer additive,
backward-compatible schema changes before code that requires them. Do not
assume that reverting application code reverses a schema change, and do not
run `migrate <previous-migration>` in production as an automatic rollback.
Prepare and review a forward fix or an owner-approved, migration-specific
recovery plan instead.

## Staging release and smoke test

1. Confirm the exact staging API hostname, isolated PostgreSQL/Redis/Celery
   services, synthetic fixture snapshot, test account, and approved release
   commit. Never use production Neon, Redis, SMTP, Cloudinary, or real user
   data.
2. Deploy the web candidate through the host's staging workflow, if one exists.
   The repository does not define that workflow; mark it unavailable if the
   provider account has no staging service.
3. Confirm the deployment log shows the expected release and successful
   migrations. Do not print environment values or credentials.
4. Run the bounded read-only smoke command from
   `docs/performance/phase-8-api-load-testing.md` with the staging target and
   a small request cap. Include `/api/health/`, one representative public read,
   and one authenticated read when a disposable account is configured.
5. Confirm the API response contract, authentication isolation, static assets,
   and frontend API origin. A `200` from `/api/health/` proves only that the
   process answered; it does not prove PostgreSQL, Redis, SMTP, Cloudinary, or
   Celery health.
6. Start or deploy the separate worker only after the web candidate and
   migrations are healthy. Beat and retention cleanup remain disabled.

## Production release

The current repository does not verify a canary or traffic-splitting feature on
the configured Render/Vercel accounts. Therefore the supported documented path
is a manually approved service deployment, not a claimed small rollout:

1. Freeze the release commit, migration plan, environment-variable checklist,
   test results, staging smoke output, and owner approvals.
2. Confirm provider backups/recovery controls and the ability to identify the
   last known-good web, worker, and frontend deployments. These provider
   controls are not visible from this repository and must be confirmed in the
   dashboards before proceeding.
3. Deploy the Render web service using its configured build/start commands.
   Wait for migration completion and the host health check before deploying or
   restarting the separate worker.
4. Deploy the worker from the same release commit with `sh worker.sh`.
5. Deploy the frontend only when its `VITE_API_BASE_URL` and API compatibility
   are unchanged or explicitly approved. The Vercel rewrite file alone does
   not identify the active project or deployment.
6. Monitor the windows and triggers below. If a required provider control,
   backup, health signal, or rollback target cannot be confirmed, stop before
   release or keep the release paused.

## Monitoring and stop/rollback triggers

Use approved owner thresholds and the pre-release baseline; the repository
contains no production SLO values. Do not invent a numeric threshold during an
incident.

| Signal | Safe source | Stop or rollback trigger |
| --- | --- | --- |
| HTTP 5xx/error rate | Render web metrics and redacted logs; bounded staging smoke output | Exceeds the owner-approved rate for the approved consecutive window, or any critical/auth/data-integrity failure |
| HTTP p50/p95 latency | Render metrics if exposed; Phase 8 harness for local/staging only | Exceeds the approved threshold or rises materially versus the same-shape baseline |
| Web health | Render health check `GET /api/health/` and deployment logs | Health check fails, process fails to boot, or migrations do not complete |
| PostgreSQL | Approved provider dashboard; local/staging `pg_stat_activity`, connection errors, and migration logs | Connection exhaustion, unavailable database, lock/CPU threshold breach, or data-integrity concern |
| Redis/cache | Approved provider memory/hit/miss/error metrics; `cache_status --json` only for the scoped subject namespace | Production cache/broker errors, memory/eviction threshold breach, or authentication/throttling impact |
| Celery worker/queue | `python manage.py celery_status --json`, worker logs, provider broker metrics | No healthy worker, persistent broker errors, rising queue depth, or approved scheduled-age/queue-delay breach |
| SMTP/Cloudinary | Application/provider error logs and synthetic staging checks only | Critical delivery/storage failure or secret/configuration error |

`celery_status --json` reports worker count, broker message count, active,
reserved, scheduled tasks, and scheduled-task age. It explicitly cannot report
the enqueue age of pending broker messages; queue delay is unavailable unless
approved enqueue/start timestamp instrumentation exists. The health endpoint
does not probe dependencies. Record unavailable signals as unavailable rather
than green.

Immediate stop triggers include an unexpected migration, missing/invalid
secret, authentication or authorization regression, exposure of private data,
database corruption, destructive task activity, or inability to identify a
known-good rollback target. Pause traffic or the affected service first when
the provider supports it; do not improvise a destructive database action.

## Rollback and recovery

### What is verified

- The web and worker are deployed as separate Render services from repository
  entrypoints.
- The repository contains no rollback script, Render service identifier,
  deploy hook, provider CLI configuration, Vercel project ID, or traffic
  routing configuration.
- No automatic rollback is safe because migrations may already have changed
  PostgreSQL state and email/Cloudinary side effects are external.

### Host-specific action required

Before a production release, the owner must confirm in Render and Vercel:

1. how to select the last known-good deployment/commit;
2. whether the account supports redeploying or rolling back that deployment;
3. whether the action affects only web, only worker, or both; and
4. whether frontend deployment history can restore the prior Vercel deployment.

Those dashboard actions are the likely rollback mechanism for the documented
hosts, but they were not verified from this repository and must not be stated
as completed or assumed available. If the host has no prior-deployment restore,
the manual recovery is to redeploy the last known-good commit through the
provider's normal deployment path after owner approval. This is a host action,
not an automatic repository command.

Do not change DNS or secrets as part of a routine rollback. Rotate a compromised
secret through the approved provider process separately, then restart/redeploy
both web and worker services as required. Never copy secrets into logs, tickets,
commands, or this runbook; `.env` is local-only and ignored by Git.

After rollback or forward recovery:

1. Confirm the provider reports the expected deployment commit and successful
   startup/migration state.
2. Check `/api/health/`, a safe public read, and an authenticated read using
   only the disposable staging account or approved production-safe check.
3. Confirm HTTP 5xx/latency return to the approved baseline window.
4. Check PostgreSQL connectivity/connections, Redis/cache errors, and Celery
   worker/queue state using the safe sources above.
5. Confirm no unintended migration, duplicate task, email, upload, or retention
   activity occurred. Keep the incident timeline and all unavailable signals
   explicitly labeled.

This repository does not contain measured production monitoring values or a
verified provider rollback transcript. Those fields remain owner/provider
actions, not claims made by this runbook.
