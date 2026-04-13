#!/bin/sh

set -eu

COMPOSE="${COMPOSE:-docker compose}"
BACKUP_PATH="${BACKUP_PATH:-${1:-}}"
DATABASE_NAME="${DATABASE__DATABASE:-helpdesk}"
DATABASE_USER="${DATABASE__USER:-helpdesk}"

if [ -z "$BACKUP_PATH" ]; then
	printf '%s\n' "Укажите BACKUP_PATH=/path/to/file.dump или первый аргумент со шляхом к backup-файлу."
	exit 1
fi

if [ ! -f "$BACKUP_PATH" ]; then
	printf '%s\n' "Backup-файл не найден: $BACKUP_PATH"
	exit 1
fi

printf '%s\n' "Восстанавливаю PostgreSQL из $BACKUP_PATH"
cat "$BACKUP_PATH" | $COMPOSE exec -T postgres pg_restore \
	-U "$DATABASE_USER" \
	-d "$DATABASE_NAME" \
	--clean \
	--if-exists \
	--no-owner \
	--no-privileges

printf '%s\n' "Restore завершён: $BACKUP_PATH"
