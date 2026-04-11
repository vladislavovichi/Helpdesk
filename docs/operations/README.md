# Эксплуатация

## Основные Команды

```bash
make docker-up
make logs
make docker-down
make health
make health-backend
```

## Runtime Контур

- PostgreSQL — persistent source of truth;
- Redis — FSM, locks, presence и runtime coordination;
- backend — внутренний gRPC сервис;
- bot — Telegram runtime поверх backend client.

## Проверка Готовности

Команда `/health` доступна операторским ролям и показывает:

- bootstrap состояние;
- доступность PostgreSQL;
- доступность Redis;
- доступность backend gRPC;
- состояние Telegram runtime.

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
