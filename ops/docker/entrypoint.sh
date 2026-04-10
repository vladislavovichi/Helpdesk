#!/bin/sh

set -eu

RUN_MIGRATIONS="${RUN_MIGRATIONS:-false}"
SERVICE_MODULE="${SERVICE_MODULE:-app.main}"

if [ "$RUN_MIGRATIONS" = "true" ]; then
	echo "Applying database migrations..."
	alembic -c migrations/alembic.ini upgrade head
fi

echo "Starting ${SERVICE_MODULE}..."
exec python -m "$SERVICE_MODULE"
