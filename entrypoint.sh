#!/bin/bash
set -e

echo "Running database migrations..."
cd /app/backend
python manage.py migrate --noinput

echo "Starting Gunicorn on port 8000..."
exec gunicorn backend.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 1 \
    --timeout 120 \
    --access-logfile -
