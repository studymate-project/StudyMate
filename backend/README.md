# StudyMate backend

This directory contains the Django and Django REST Framework API for StudyMate.
It is intentionally a small foundation: PostgreSQL configuration, secure
environment-driven settings, CORS/CSRF preparation, and a health endpoint.

The pre-existing Django project package remains named `backend`. The domain
layer is split into these applications:

- `apps.users` — `StudentProfile`, linked one-to-one with the configured
  Django user model.
- `apps.education` — education backgrounds, courses, flexible academic levels,
  interests, and student-interest relationships.
- `apps.resources` — resources, tags, event-based views/downloads, and
  YouTube-reference videos.
- `apps.community` — questions and answers.
- `apps.interactions` — saves, upvotes, and follows, protected by database
  uniqueness constraints (and a self-follow check constraint).
- `apps.notifications` — recipient-owned notifications with an optional
  generic reference to the relevant domain object.

This project intentionally keeps Django's default user model. Every domain
relationship references `settings.AUTH_USER_MODEL`, so a future user-model
decision does not require hard-coded imports. Content file fields store a
storage reference, not binary data; video records store a normalized YouTube
video ID rather than hosted media.

The current migrations are PostgreSQL migrations. Run them with:

```powershell
python manage.py migrate
python manage.py makemigrations --check
```

## Local setup

From this directory, create and activate a virtual environment (PowerShell):

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements\base.txt
Copy-Item .env.example .env
```

Set a unique `SECRET_KEY` in `.env`; the comment in `.env.example` includes a
command that generates one. `.env` is ignored and must never be committed.
For a production deployment, set `DEBUG=False`, use HTTPS origins, and retain
the `SECURE_SSL_REDIRECT` and `SECURE_HSTS_SECONDS` values from the example.
Set `ALLOWED_HOSTS` to the Render hostname, and set both
`CORS_ALLOWED_ORIGINS` and `CSRF_TRUSTED_ORIGINS` to the exact HTTPS Vercel
`FRONTEND_URL` to that same exact HTTPS Vercel origin. `CORS_ALLOWED_ORIGINS`
must contain only `FRONTEND_URL`; `CSRF_TRUSTED_ORIGINS` must contain it and
may additionally contain an explicitly configured HTTPS backend origin when
needed by the existing cookie-auth architecture. Because the frontend and API are cross-site, production cookie auth
also requires `JWT_COOKIE_SAMESITE=None` and `JWT_COOKIE_SECURE=True`; CSRF
protection remains required for unsafe requests.

Production settings reject placeholder/semi-shared secrets, non-PostgreSQL
databases, wildcard hosts, insecure origins, insecure cookies, and partial
Cloudinary credentials during startup. Durable Cloudinary media storage is
required when `DEBUG=False`. Refresh-token rotation and blacklisting are enabled
by default when `DEBUG=False`; run `python manage.py migrate` so the SimpleJWT
blacklist tables exist.

Cloudinary is optional in local development. Set `CLOUDINARY_CLOUD_NAME`,
`CLOUDINARY_API_KEY`, and `CLOUDINARY_API_SECRET` together to initialize the
server-side Cloudinary SDK and enable the `cloudinary_media` storage alias.
This foundation deliberately leaves the existing `Resource.file` field and
database references unchanged; new production uploads use the configured
Cloudinary storage alias while existing records are not migrated.
Resource uploads are server-validated against their resource type, file
signature, allowed content type, and `RESOURCE_MAX_FILE_SIZE_BYTES` (20 MiB by
default). Existing metadata-only Resource creation remains supported.
When configured, new validated files are uploaded by Django into the
`CLOUDINARY_RESOURCE_FOLDER` hierarchy and the existing `Resource.file` field
stores a Cloudinary reference. Local filesystem storage is available only when
`DEBUG=True`.

## Render deployment

Set the Render service root directory to `backend`.

Build Command:

```text
pip install -r requirements/base.txt && python manage.py collectstatic --noinput
```

Start Command:

```text
sh start.sh
```

Set this as the service's Render Start Command. Existing Render services
configured with the previous Gunicorn command need this one-time dashboard
setting update; after that, every deployment runs the committed startup
script.

Do not use Django's development server on Render. `start.sh` applies all
pending migrations with `--noinput` and only starts Gunicorn if migrations
complete successfully. This includes the production-only
`token_blacklist` migrations that create the SimpleJWT outstanding-token and
blacklisted-token tables.

The health-check URL is `https://<render-service>.onrender.com/api/health/`.
Configure Render's health check path to `/api/health/`.

Required Render environment variables:

- `SECRET_KEY`: unique high-entropy Django secret.
- `DEBUG=False`.
- `DATABASE_URL`: Render PostgreSQL connection string.
- `DB_SSLMODE=require`.
- `ALLOWED_HOSTS`: the exact Render hostname, plus any configured custom API hostname.
- `FRONTEND_URL`: the exact HTTPS Vercel origin.
- `CORS_ALLOWED_ORIGINS`: exactly the same HTTPS Vercel origin.
- `CSRF_TRUSTED_ORIGINS`: the same HTTPS Vercel origin.
- `JWT_SIGNING_KEY`: unique high-entropy key different from `SECRET_KEY`.
- `JWT_COOKIE_SECURE=True`.
- `JWT_COOKIE_SAMESITE=None`.
- `JWT_TOKEN_BLACKLIST_ENABLED=True`.
- `REDIS_URL`: Upstash `rediss://` URL for the shared cache.
- `CELERY_BROKER_URL`: Upstash `rediss://` broker URL, unless the worker intentionally reuses `REDIS_URL`.
- `DEFAULT_FROM_EMAIL`.
- `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, and the appropriate `EMAIL_USE_TLS` or `EMAIL_USE_SSL` setting.
- `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET`.
- `LOG_LEVEL=INFO`.

Optional Render variables include the JWT lifetimes, Cloudinary folders,
database connection bounds, throttling rates, and cookie domain. Render
provides `PORT`; it must not be committed or hard-coded.

Required Vercel environment variable:

```text
VITE_API_BASE_URL=https://<render-service>.onrender.com/api
```

Replace the placeholder with the deployed Render API origin and redeploy the
Vercel frontend after changing it.

## PostgreSQL

Create a PostgreSQL database and role, then set `DATABASE_URL` in `.env` using
this form:

```text
postgresql://USER:PASSWORD@HOST:PORT/DATABASE_NAME
```

PostgreSQL is the only configured database for development and production; no
SQLite fallback is provided. Once the database is reachable, run:

```powershell
python manage.py migrate
```

Render should provide its PostgreSQL `DATABASE_URL` as a secret environment
variable and set `DB_SSLMODE=require`. Production defaults to TLS-required
PostgreSQL connections; local development leaves SSL mode to the local URL.
`DB_CONN_MAX_AGE=0` and health checks are the safe defaults for Render workers;
only increase connection reuse after sizing the worker count against the
database connection limit.

## Run the API

```powershell
python manage.py check
python manage.py runserver
```

The public health check is available at `GET /api/health/` and returns:

```json
{"status": "ok"}
```

## Architecture

`frontend/` remains a separate React/Vite client. The API is served from
`/api/`; CORS is limited to `CORS_ALLOWED_ORIGINS`, and CSRF trusted origins
are configured separately for HTTP-only-cookie authentication. Browser clients
can request `/api/auth/csrf/` to bootstrap Django's CSRF cookie and receive the
non-secret token before
unsafe cookie-authenticated requests. Future APIs can be grouped under `/api/auth/`, `/api/users/`,
`/api/education/`, `/api/resources/`, `/api/videos/`, `/api/questions/`,
`/api/notifications/`, and `/api/search/`.

The backend includes the domain models, migrations, authentication/JWT flow,
uploads, Cloudinary storage, and Celery-backed signup verification email
delivery. Signup OTPs are sent by a separate worker through Django's configured
email backend; the web process never sends them synchronously.

## Celery and Upstash Redis

Set `CELERY_BROKER_URL` to an Upstash TLS connection URL. The existing
`REDIS_URL` is used as a fallback so one Upstash database can support both the
cache and Celery, but a separate broker URL may be configured when preferred.
Do not commit the password. The expected format is:

```text
rediss://default:<UPSTASH_PASSWORD>@<UPSTASH_ENDPOINT>:6379/0?ssl_cert_reqs=required
```

URL-encode the password when it contains reserved URL characters. Production
requires the `rediss://` TLS scheme. Configure `DEFAULT_FROM_EMAIL` and the
normal Django email-backend/SMTP variables as well.

Run a worker locally from `backend/` with:

```powershell
python -m celery -A backend.celery worker --loglevel=INFO
```

Production needs a separate long-running worker process using the same command
(and the production environment variables); the existing Gunicorn web
process does not run Celery workers. For Render, create a separate Background
Worker service with root directory `backend`, the same environment variables as
the web service, and this Start Command:

```text
sh worker.sh
```

The committed `worker.sh` entrypoint keeps the worker command consistent across
local development and production. Deploy the web service first so its startup
migration completes, then start the worker service. A deployment must apply
committed Django migrations, including the signup verification migration,
before serving traffic.
