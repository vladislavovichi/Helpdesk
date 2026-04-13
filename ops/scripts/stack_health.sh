#!/bin/sh

set -eu

COMPOSE="${COMPOSE:-docker compose}"
STACK_SERVICES="${STACK_SERVICES:-postgres redis ai-service backend bot}"

service_status() {
	service="$1"
	container_id="$($COMPOSE ps -q "$service")"
	if [ -z "$container_id" ]; then
		printf '%s' "missing"
		return
	fi

	docker inspect \
		--format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' \
		"$container_id" 2>/dev/null || printf '%s' "unknown"
}

printf '%s\n' "STACK"
exit_code=0

for service in $STACK_SERVICES; do
	status="$(service_status "$service")"
	case "$status" in
		healthy|running)
			printf '[OK] service/%s: %s\n' "$service" "$status"
			;;
		starting|created|restarting)
			printf '[WARN] service/%s: %s\n' "$service" "$status"
			exit_code=1
			;;
		missing|unknown|unhealthy|exited|dead)
			printf '[FAIL] service/%s: %s\n' "$service" "$status"
			exit_code=1
			;;
		*)
			printf '[WARN] service/%s: %s\n' "$service" "$status"
			exit_code=1
			;;
	esac
done

exit "$exit_code"
