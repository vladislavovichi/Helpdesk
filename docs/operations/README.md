# Эксплуатация

## Контур

- `postgres` хранит заявки, операторов, категории, заметки, feedback, аудит и AI summary cache;
- `redis` держит FSM, locks, presence, streams и SLA coordination;
- `ai-service` обслуживает внутренний gRPC-контур AI;
- `backend` содержит продуктовые правила и gRPC API;
- `bot` работает как Telegram presentation/runtime слой поверх `backend`.

## Основные Команды

```bash
make up
make ps
make health
make smoke
make logs
make logs-backend
make logs-ai
make backup-db
make down
```

`make health` показывает состояние контейнеров Docker Compose.  
`make health-bot`, `make health-backend` и `make health-ai` запускают прикладные probes и печатают правдивую readiness-диагностику самих сервисов.

## Что Считать Нормальным Стартом

1. `postgres` и `redis` становятся healthy.
2. `ai-service` поднимает gRPC и начинает отвечать на внутренний status probe.
3. `backend` выполняет миграции, проверяет БД, Redis и `ai-service`, а потом становится ready.
4. `bot` проверяет БД, Redis и `backend`, а потом считается готовым.

Если один из этих шагов не проходит, сервис должен завершиться явно, а не зависнуть в полуготовом состоянии.

## Readiness И Operational Truth

- `postgres` healthy, когда `pg_isready` видит базу;
- `redis` healthy, когда отвечает `PING`;
- `ai-service` healthy, когда живой gRPC endpoint отвечает на auth-protected status call;
- `backend` healthy, когда доступны БД, Redis, `ai-service` и сам backend gRPC отвечает на internal status call;
- `bot` healthy, когда внутренняя диагностика подтверждает зависимости и runtime surfaces.

Для `ai-service` отдельно виден operational mode:

- `OK` — gRPC жив, auth настроен, provider включён;
- `DEGRADED` — сервис жив, но provider отключён или не настроен; продукт продолжает работать с graceful degradation;
- `FAIL` — сервис недоступен или auth/config сломан.

## Runbook-и

- [Деплой и обновление](runbooks/deploy.md)
- [Диагностика и типовые сбои](runbooks/diagnostics.md)
- [Backup и restore PostgreSQL](runbooks/backup-restore.md)

## Что Ещё Важно

- `/health` в Telegram остаётся быстрым операторским срезом состояния runtime;
- backend продолжает писать структурный audit trail по чувствительным действиям;
- Redis не считается источником долговременной правды и не входит в backup-процедуру;
- smoke-check не заменяет тесты, а подтверждает, что стек реально поднялся и основные цепочки доступны.
