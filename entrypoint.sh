#!/bin/bash
set -e

echo "Running database migrations..."
cd /app/backend
python manage.py migrate --noinput

echo "Starting Gunicorn on port 7860..."
exec gunicorn backend.wsgi:application \
    --bind 0.0.0.0:7860 \
    --workers 1 \
    --timeout 120 \
    --access-logfile -
