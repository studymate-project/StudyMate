#!/bin/sh
set -eu

# Render runs this from the service root, but resolving the script directory
# keeps the entrypoint correct when it is invoked from another working folder.
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$SCRIPT_DIR"

# Run this as a separate long-lived process from the Gunicorn web service.
exec python -m celery -A backend.celery worker \
  --loglevel="${CELERY_LOG_LEVEL:-INFO}" \
  --hostname="${CELERY_WORKER_NAME:-studymate@%h}"
