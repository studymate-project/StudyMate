#!/bin/sh
set -eu

# Apply every committed Django migration before serving requests. This is
# required for production-only apps such as SimpleJWT's token blacklist.
python manage.py migrate --noinput

exec gunicorn backend.wsgi:application \
  --bind "0.0.0.0:${PORT:-8000}" \
  --access-logfile - \
  --error-logfile -
