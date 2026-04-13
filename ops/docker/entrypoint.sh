#!/bin/sh

set -eu

RUN_MIGRATIONS="${RUN_MIGRATIONS:-false}"
SERVICE_MODULE="${SERVICE_MODULE:-app.main}"

log() {
	printf '%s %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$*"
}

if [ "$RUN_MIGRATIONS" = "true" ]; then
	log "Applying database migrations for ${SERVICE_MODULE}"
	alembic -c migrations/alembic.ini upgrade head
	log "Database migrations completed for ${SERVICE_MODULE}"
fi

log "Starting ${SERVICE_MODULE}"
exec python -m "$SERVICE_MODULE"
