# Reliora

`Reliora` — Telegram helpdesk с русскоязычным интерфейсом для операторов и отдельным backend-сервисом на gRPC.

## Что Уже Есть

- intake по темам и создание заявки из первого сообщения;
- live-диалог клиента и оператора;
- очередь и персональные рабочие заявки;
- архив закрытых кейсов с кнопочным просмотром;
- HTML/CSV экспорт по заявке;
- HTML/CSV экспорт аналитики;
- категории, метки, макросы, заметки и feedback;
- роли `user`, `operator`, `super_admin`;
- Redis-backed FSM, runtime locks и явный gRPC boundary.

## Production Hardening

Текущий контур дополнительно усиливает эксплуатационную часть:

- fail-fast startup checks для PostgreSQL, Redis, bot config и internal gRPC auth;
- internal auth metadata между bot и backend;
- correlation id через bot -> gRPC -> backend logs;
- structured audit log для чувствительных действий;
- более безопасные `CSV` / `HTML` экспорты;
- ограничение и валидация входящих вложений;
- более предсказуемые timeout/retry правила для Telegram delivery и read-only gRPC calls.

## Архитектурная Идея

Направление потока простое:

```text
Telegram bot -> gRPC client -> backend service -> application use cases -> domain contracts -> infrastructure
```

Это позволяет держать Telegram presentation тонким, а продуктовые сценарии расширять без размывания границ.

## Быстрый Старт

```bash
cp .env.example .env
make install
make migrate
make run-backend
make run-bot
```

Если нужен локальный прогон без реального polling:

```dotenv
APP__DRY_RUN=true
```

Основные developer entrypoint'ы:

```bash
make test
make lint
make check
make docker-up
make full
```

## Документация

- [Продукт и UX](docs/product/README.md)
- [Архитектура](docs/architecture/README.md)
- [Backend и gRPC](docs/backend/README.md)
- [Telegram bot](docs/bot/README.md)
- [Разработка](docs/development/README.md)
- [Эксплуатация](docs/operations/README.md)
