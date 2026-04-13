#!/bin/sh

set -eu

COMPOSE="${COMPOSE:-docker compose}"
BACKUP_DIR="${BACKUP_DIR:-backups/postgres}"
DATABASE_NAME="${DATABASE__DATABASE:-helpdesk}"
DATABASE_USER="${DATABASE__USER:-helpdesk}"
TIMESTAMP="$(date -u '+%Y%m%dT%H%M%SZ')"
OUTPUT_PATH="${BACKUP_PATH:-$BACKUP_DIR/helpdesk_${TIMESTAMP}.dump}"

mkdir -p "$BACKUP_DIR"

printf '%s\n' "Создаю backup PostgreSQL: $OUTPUT_PATH"
$COMPOSE exec -T postgres pg_dump \
	-U "$DATABASE_USER" \
	-d "$DATABASE_NAME" \
	-Fc \
	--no-owner \
	--no-privileges > "$OUTPUT_PATH"

printf '%s\n' "Backup завершён: $OUTPUT_PATH"
