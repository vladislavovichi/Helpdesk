# Диагностика и типовые сбои

## С чего начать

Если стек ведёт себя не так, как ожидается, обычно достаточно пройти один и тот же короткий маршрут:

```bash
make ps
make health
make logs-backend
make smoke
```

Этого хватает, чтобы отделить проблему контейнера от проблемы конфигурации и от проблемы внутри самой службы.

## Где смотреть

- `make logs-backend` — миграции, PostgreSQL, Redis, доступность `ai-service`, внутренняя авторизация;
- `make logs-ai` — состояние AI-провайдера, ошибки внешнего API, внутренний gRPC;
- `make logs-bot` — запуск Telegram-слоя, связь с `backend`, ошибки polling;
- `make logs-mini-app` — запуск Mini App gateway, состояние `MINI_APP__PUBLIC_URL`, ошибки HTTP;
- `make health-backend` — прикладная проверка `backend`;
- `make health-ai` — прикладная проверка `ai-service`;
- `make health-bot` — внутренняя диагностика bot-процесса.
- `curl http://127.0.0.1:8088/healthz` — локальная проверка Mini App endpoint.

## Если недоступен `backend`

Проверьте:

```bash
make logs-backend
make health-backend
```

Чаще всего причина одна из этих:

- неверные `DATABASE__*`;
- Redis не отвечает;
- `ai-service` недоступен по gRPC;
- токен `AI_SERVICE_AUTH__TOKEN` не совпадает;
- миграция завершилась ошибкой.

## Если недоступен `ai-service`

Проверьте:

```bash
make logs-ai
make health-ai
```

Здесь важно различать две ситуации.

Первая: служба жива, но провайдер отключён или не настроен. Тогда основной контур продолжает работать без AI-подсказок.

Вторая: сама служба недоступна по gRPC. Тогда `backend` не сможет выйти в готовность, и это уже влияет на весь стек.

## Если проблема в PostgreSQL

Характерные признаки:

- `backend` не проходит проверку зависимости `postgresql`;
- `smoke` падает в самом начале;
- в логах видны `SQLAlchemyError`, timeout или connection refused.

Что проверить:

1. состояние контейнера `postgres`;
2. значения `DATABASE__HOST`, `DATABASE__PORT`, `DATABASE__USER`, `DATABASE__PASSWORD`, `DATABASE__DATABASE`;
3. состояние volume с данными.

## Если проблема в Redis

Обычно это проявляется так:

- `bot` не поднимает свои рабочие поверхности;
- `backend` или `bot` падают на startup dependency check `redis`;
- часть интерактивных сценариев ведёт себя так, будто контекст потерян.

Redis в проекте нужен для координации во время работы, но не является долговременным источником данных. После его восстановления стоит сразу прогнать `make health` и `make smoke`.

## Если не видно кнопку Mini App

Проверьте три вещи по порядку:

1. `MINI_APP__PUBLIC_URL` задан и это публичный `HTTPS` адрес.
2. В логах `bot` или `mini-app` нет предупреждения про невалидный Mini App URL.
3. Сам HTTP endpoint Mini App отвечает локально.

Быстрый маршрут:

```bash
make logs-bot
make logs-mini-app
make health-bot
curl http://127.0.0.1:8088/healthz
```

Что считать проблемой конфигурации:

- URL пустой;
- используется `http://`;
- указан `localhost`, приватный IP или локальный домен;
- `mini-app` поднят, но `GET /healthz` не отвечает.

В `bot /health` Mini App показывается отдельными проверками:

- `mini_app_url` — сконфигурирован ли Telegram-валидный launch URL;
- `mini_app_http` — отвечает ли сам Mini App endpoint.

## Как читать startup checks

В логах startup dependency checks есть классификация ошибки:

- `auth_issue` — проблема во внутренней авторизации;
- `config_issue` — неправильная или неполная конфигурация;
- `dependency_issue` — сеть, порт, контейнер или внешняя зависимость;
- `runtime_issue` — сбой уже внутри кода.

Этого обычно достаточно, чтобы быстро понять, с какой стороны подступаться к проблеме.
