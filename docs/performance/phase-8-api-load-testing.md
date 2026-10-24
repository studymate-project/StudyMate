# Phase 8 API load-test tooling

`tools/api_load_test.py` is a small, standard-library-only harness for bounded,
read-only API smoke tests. No Locust, k6, Artillery, or other load-test tool is
installed in the repository environment, so this script does not add a new
dependency.

The harness is deliberately fail-closed:

- `--base-url` and `--target-environment {local,staging}` are required.
- Local targets must be loopback (`localhost`, `127.0.0.1`, or `::1`).
- Staging targets require an exact `--staging-hostname` whose hostname includes
  `staging`, `stage`, `qa`, `test`, or `dev`.
- Production-looking hostnames and recognizable production database/cache/broker
  URLs are rejected. The script never reads `.env` files or Django settings.
- Only the read-only endpoint allowlist in the script is available. Signup,
  login, refresh, logout, interactions, uploads, and all other mutating routes
  are not load-test targets.
- Requests are not retried. The default workload is 10 seconds, one worker, one
  request per second, and at most 20 requests. Each value has a hard upper
  bound; `--dry-run` validates configuration without sending traffic.
- Authentication uses a bearer token from an explicitly named environment
  variable. The token is never printed. Test accounts must already exist in the
  local/staging environment; the tool never creates accounts.

## Local smoke test

Start the API against a disposable local PostgreSQL database and any required
local services using the normal project setup. From the repository root:

```powershell
python tools/api_load_test.py `
  --base-url http://127.0.0.1:8000 `
  --target-environment local `
  --endpoint health `
  --duration 10 `
  --concurrency 1 `
  --rate 1 `
  --max-requests 20 `
  --timeout 5
```

Validate without sending requests:

```powershell
python tools/api_load_test.py `
  --base-url http://127.0.0.1:8000 `
  --target-environment local `
  --endpoint health `
  --dry-run `
  --format json
```

For an authenticated read-only endpoint, provide a disposable test account's
access token without putting it on the command line:

```powershell
$env:STUDYMATE_LOADTEST_TOKEN = '<local-or-staging-test-token>'
python tools/api_load_test.py `
  --base-url http://127.0.0.1:8000 `
  --target-environment local `
  --endpoint notifications `
  --auth-mode bearer `
  --auth-token-env STUDYMATE_LOADTEST_TOKEN `
  --account-label phase8-local-reader `
  --duration 10 `
  --concurrency 1 `
  --rate 1 `
  --max-requests 20
Remove-Item Env:STUDYMATE_LOADTEST_TOKEN
```

A staging example must use the exact staging hostname and a hostname marker:

```powershell
python tools/api_load_test.py `
  --base-url https://api-staging.example.test `
  --target-environment staging `
  --staging-hostname api-staging.example.test `
  --endpoint search `
  --duration 10 `
  --concurrency 1 `
  --rate 1 `
  --max-requests 20
```

The example hostname is a placeholder and must not be used as a real target.
Do not run the harness with a production URL, production `DATABASE_URL`,
`REDIS_URL`, or `CELERY_BROKER_URL`. The script cannot prove the server-side
configuration, so the operator must separately verify that the selected local
or staging API uses disposable data and services.

## Output and cleanup

The output records the tool and Python versions, target hostname and
environment, endpoint, authentication label, configured duration/concurrency/
rate/request limit/timeout, request count, HTTP status counts, errors,
timeouts, throughput, and p50/p95 latency. It reports observations only; it
does not produce before/after claims or performance budgets.

The harness creates no database rows, files, accounts, uploads, queues, or
retention jobs. Cleanup is therefore limited to stopping the local API and
removing the temporary token environment variable. Any disposable PostgreSQL
or Redis data should be discarded using the local service's normal cleanup
procedure after the API is stopped. Do not run Celery Beat or retention cleanup
for this exercise.

No high-load run is part of implementation. A later operator should begin with
the documented smoke defaults, review the output, and obtain explicit approval
before increasing the bounded workload.
