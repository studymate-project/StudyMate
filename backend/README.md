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

Cloudinary is optional in local development. Set `CLOUDINARY_CLOUD_NAME`,
`CLOUDINARY_API_KEY`, and `CLOUDINARY_API_SECRET` together to initialize the
server-side Cloudinary SDK and enable the `cloudinary_media` storage alias.
This foundation deliberately leaves the existing `Resource.file` filesystem
storage unchanged; migrating that field and existing records is a later step.
Resource uploads are server-validated against their resource type, file
signature, allowed content type, and `RESOURCE_MAX_FILE_SIZE_BYTES` (20 MiB by
default). Existing metadata-only Resource creation remains supported.
When configured, new validated files are uploaded by Django into the
`CLOUDINARY_RESOURCE_FOLDER` hierarchy and the existing `Resource.file` field
stores a Cloudinary reference. Local filesystem storage remains the fallback
when Cloudinary credentials are absent.

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
can request `/api/auth/csrf/` to bootstrap Django's readable CSRF cookie before
unsafe cookie-authenticated requests. Future APIs can be grouped under `/api/auth/`, `/api/users/`,
`/api/education/`, `/api/resources/`, `/api/videos/`, `/api/questions/`,
`/api/notifications/`, and `/api/search/`.

The backend includes the domain models, migrations, authentication/JWT flow,
uploads, and an optional Cloudinary storage foundation. Redis and Celery have
not been implemented.
