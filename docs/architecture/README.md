# Архитектура Reliora

## Слои

- `src/bot` — Telegram presentation: handlers, keyboards, formatters, texts, middlewares.
- `src/backend` — отдельный gRPC transport layer и server runtime.
- `src/application` — use cases, orchestration и продуктовые операции.
- `src/domain` — сущности, инварианты и контракты репозиториев.
- `src/infrastructure` — PostgreSQL, Redis, exports, config, logging.
- `src/app` — runtime Telegram-бота и клиентская health-проверка.

## Главные Правила

- handlers не принимают бизнес-решения и не работают напрямую с БД;
- backend публикует явные protobuf/gRPC контракты;
- application не знает о Telegram и protobuf;
- exports рендерятся отдельными модулями;
- аналитика и архив не привязаны к Telegram transport;
- PostgreSQL остаётся source of truth, Redis — runtime-слой.

## Текущий Transport Boundary

Через внутренний gRPC уже идут:

- создание заявки и intake;
- карточка заявки и список очереди;
- активные заявки оператора;
- reply, close, assign, macros;
- analytics snapshot и exports;
- archived ticket browsing и historical exports.

## Почему Это Важно

Такой контур позволяет:

- развивать продукт без размазывания логики по presentation-коду;
- проверять бизнес-поведение на application/backend уровне;
- удерживать premium Telegram UX при растущей backend-сложности.
