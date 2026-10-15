#!/bin/sh
set -eu

# Run this as a separate long-lived process from the Gunicorn web service.
exec python -m celery -A backend.celery worker \
  --loglevel="${CELERY_LOG_LEVEL:-INFO}" \
  --hostname="${CELERY_WORKER_NAME:-studymate@%h}"
