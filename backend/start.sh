#!/bin/sh
set -eu

# Render runs this from the service root, but resolving the script directory
# keeps the entrypoint correct when it is invoked from another working folder.
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$SCRIPT_DIR"

# Apply every committed Django migration before serving requests. This is
# required for production-only apps such as SimpleJWT's token blacklist.
python manage.py migrate --noinput

exec gunicorn backend.wsgi:application \
  --bind "0.0.0.0:${PORT:-8000}" \
  --access-logfile - \
  --error-logfile -
