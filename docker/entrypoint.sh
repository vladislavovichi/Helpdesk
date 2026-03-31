#!/bin/sh

set -eu

echo "Applying database migrations..."
alembic upgrade head

echo "Starting application..."
exec python -m app.main
