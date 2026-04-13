# Диагностика И Типовые Сбои

## Базовая Последовательность

1. `make ps`
2. `make health`
3. `make logs-backend` или `make logs-ai`
4. `make smoke`

Обычно этого достаточно, чтобы быстро понять, проблема в конфиге, зависимости или уже в runtime-логике.

## Где Смотреть Что

- `make logs-backend` — миграции, БД, Redis, доступность `ai-service`, внутренний gRPC auth;
- `make logs-ai` — состояние AI provider, ошибки внешнего inference API, internal auth;
- `make logs-bot` — старт Telegram runtime, недоступность backend, проблемы polling;
- `make health-backend` — truthy probe backend: auth, БД, Redis, `ai-service`, собственный gRPC;
- `make health-ai` — truthy probe `ai-service`: auth, живой gRPC, operational mode provider;
- `make health-bot` — диагностика зависимостей и готовности bot runtime.

## Если Недоступен Backend

Сначала проверить:

```bash
make logs-backend
make health-backend
```

Частые причины:

- сломана БД или неверные `DATABASE__*`;
- недоступен Redis;
- `AI_SERVICE_AUTH__TOKEN` не совпадает;
- `ai-service` не отвечает по gRPC;
- миграция упала и backend завершился до готовности.

## Если Недоступен AI Service

Проверки:

```bash
make logs-ai
make health-ai
```

Что важно понимать:

- если provider отключён, `ai-service` может быть `DEGRADED`, но сам сервис всё ещё операбелен;
- если gRPC `ai-service` недоступен полностью, `backend` тоже не станет ready;
- graceful degradation относится к самим AI-ответам, а не к отсутствию внутреннего `ai-service` runtime.

## Если Проблема В PostgreSQL

Симптомы:

- `backend` не проходит startup dependency check `postgresql`;
- `bot` и smoke-check валятся ещё до полезных функциональных шагов;
- в логах backend виден `SQLAlchemyError`, timeout или connection refused.

Что делать:

1. Проверить контейнер `postgres` через `make health`.
2. Проверить, совпадают ли `DATABASE__USER`, `DATABASE__PASSWORD`, `DATABASE__DATABASE`.
3. Проверить, не изменился ли volume и не стартовал ли стек на пустом каталоге данных.

## Если Проблема В Redis

Симптомы:

- `bot` не готовит FSM/runtime surfaces;
- startup dependency checks на `redis` падают у `backend` или `bot`;
- часть live workflow surfaces недоступна.

Redis здесь важен для runtime-координации, но не является долговременным источником данных. После восстановления Redis нужно в первую очередь убедиться, что `backend` и `bot` снова проходят health/smoke.

## Если Похоже На Auth Или Config Drift

Смотрите на тип ошибки в логах startup dependency checks:

- `failure_class=auth_issue` — обычно токен или внутренний caller/auth drift;
- `failure_class=config_issue` — некорректный env или отсутствующий обязательный параметр;
- `failure_class=dependency_issue` — сеть, контейнер, порт, БД, Redis, gRPC endpoint;
- `failure_class=runtime_issue` — проблема уже внутри кода или неожиданный сбой инициализации.
