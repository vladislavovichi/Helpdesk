# Эксплуатация

## Основные Команды

```bash
make docker-up
make logs
make docker-down
make health
make health-backend
make migrate
```

## Runtime Контур

- PostgreSQL — persistent source of truth;
- Redis — FSM, locks, presence и runtime coordination;
- backend — внутренний gRPC сервис;
- bot — Telegram runtime поверх backend client.

## Startup И Readiness

Оба процесса стартуют по одной логике:

- сначала проверяется обязательная конфигурация;
- затем выполняются ограниченные readiness-checks зависимостей;
- при критической ошибке процесс завершается сразу;
- structured logs содержат dependency name, target, attempt и correlation id.

Критичные условия для старта:

- `AUTHORIZATION__SUPER_ADMIN_TELEGRAM_USER_IDS`;
- `BACKEND_AUTH__TOKEN`;
- для bot runtime при `APP__DRY_RUN=false` ещё и `BOT__TOKEN`;
- доступность PostgreSQL и Redis;
- для bot runtime дополнительно доступность backend gRPC.

## Health И Диагностика

`make health` и `make health-backend` выводят:

- `liveness`;
- `readiness`;
- детализацию по dependency и runtime checks.

Команда `/health` доступна операторским ролям и показывает:

- liveness и readiness статус;
- internal backend auth readiness;
- доступность PostgreSQL;
- доступность Redis;
- доступность backend gRPC;
- состояние Telegram runtime.

## Внутренний gRPC Auth

Bot и backend обмениваются internal metadata:

- `x-helpdesk-internal-token`;
- `x-helpdesk-caller`;
- `x-correlation-id`;
- `x-helpdesk-actor-telegram-user-id` там, где это нужно для аудита и trace.

Если token отсутствует или не совпадает, backend отклоняет запрос до бизнес-логики.

## Audit Trail

Для чувствительных действий backend пишет структурные записи в `audit_logs`:

- ticket take / close / escalate / reassign / macro / tags / internal notes;
- ticket и analytics export;
- category и macro management;
- operator role grant / revoke;
- feedback mutations, когда они реально сохранены или уже были зафиксированы.

Каждая запись хранит actor, action, entity, outcome, correlation id и metadata JSON.

## Экспорты И Вложения

- CSV export экранирует formula-like значения;
- HTML export не встраивает небезопасные image MIME type и не позволяет выйти из asset root;
- internal notes попадают в ticket export только при `EXPORTS__INCLUDE_INTERNAL_NOTES_IN_TICKET_REPORTS=true`;
- входящие вложения ограничены по размеру и не принимают исполняемые документы.

## Docker

Основные artefact'ы лежат в `ops/docker/`:

- `Dockerfile`
- `compose.yml`
- `entrypoint.sh`
- `full.sh`

Полный локальный happy-path:

```bash
make full
```
