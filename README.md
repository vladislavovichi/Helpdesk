# Reliora

`Reliora` — Telegram helpdesk для клиентской поддержки внутри одного бота. Проект принимает обращения, ведет живой диалог между клиентом и оператором, управляет очередью, ролями, макросами, тегами и операционной диагностикой.

## Что это за проект

Проект собран как production-oriented backend с явным `src/` layout, PostgreSQL для долговременного состояния, Redis для runtime-механик и `aiogram` для Telegram delivery.

Репозиторий разделен по слоям:

- `bot` отвечает за Telegram UX, тексты, клавиатуры и обработку update'ов;
- `application` собирает продуктовые сценарии и orchestration;
- `domain` хранит сущности, enum'ы, правила и контракты;
- `infrastructure` инкапсулирует PostgreSQL, Redis, конфигурацию и logging;
- `app` поднимает runtime, bootstrap и health-проверки.

## Возможности

- прием первого клиентского сообщения с автоматическим созданием заявки;
- продолжение диалога внутри уже открытой заявки;
- операторская очередь с пагинацией и кнопочными сценариями;
- активный контекст заявки для live-переписки;
- эскалация, закрытие и переназначение заявок;
- библиотека макросов с просмотром, отправкой и администрированием;
- теги и каталог тегов для операторов;
- статистика и диагностические проверки;
- роли `user`, `operator`, `super_admin`;
- Redis-backed FSM и runtime locks для конкурентных действий.

## Архитектура

Рабочий поток выглядит так:

1. Telegram update попадает в `bot`.
2. Handler вызывает `application`-сервис.
3. Сервис делегирует use case'ам и доменным правилам.
4. `infrastructure` выполняет чтение, запись, блокировки, storage и delivery-поддержку.

Ожидаемое направление зависимостей:

```text
bot -> application -> domain/contracts -> infrastructure
```

Принципиальные ограничения:

- `bot` не принимает продуктовых решений и не работает с raw DB/session;
- `application` не знает о Telegram-разметке и клавиатурах;
- `infrastructure` не определяет бизнес-правила helpdesk;
- тексты, форматтеры и клавиатуры остаются presentation-слоем.

## Роли и сценарии

**Пользователь**

- пишет в бот;
- получает подтверждение создания заявки;
- продолжает переписку по открытому обращению;
- может завершить заявку кнопкой из карточки клиента.

**Оператор**

- берет заявки из очереди;
- ведет диалог в активном контексте;
- применяет макросы;
- меняет теги;
- закрывает, эскалирует и переназначает заявки;
- смотрит операционную статистику.

**Суперадминистратор**

- имеет все возможности оператора;
- управляет составом операторов;
- управляет библиотекой макросов.

Суперадминистраторы задаются через `.env`:

```dotenv
AUTHORIZATION__SUPER_ADMIN_TELEGRAM_USER_IDS=12345,67890
```

## Быстрый старт

Требования:

- Python `3.12+`
- Poetry
- PostgreSQL и Redis, либо Docker Compose
- заполненный `.env`

Локальный старт:

```bash
cp .env.example .env
make install
make migrate
make health
make run
```

Если нужен только bootstrap без Telegram polling, оставьте:

```dotenv
APP__DRY_RUN=true
```

Фактический entrypoint приложения:

```bash
PYTHONPATH=src poetry run python -m app.main
```

## Запуск через Docker

Полный happy-path запуск со сборкой и проверкой health:

```bash
make full
```

Базовые команды:

```bash
make docker-up
make logs
make docker-down
```

Контейнер `app`:

- ждет готовности `postgres` и `redis`;
- применяет `alembic upgrade head` на старте;
- поднимает приложение;
- публикует healthcheck через `python -m app.healthcheck`.

## Конфигурация

Настройки читаются через `pydantic-settings` и сгруппированы по секциям:

- `app`
- `bot`
- `authorization`
- `database`
- `redis`
- `logging`

Базовый набор переменных:

```dotenv
APP__NAME=tg-helpdesk
APP__ENVIRONMENT=dev
APP__DRY_RUN=true

BOT__TOKEN=

AUTHORIZATION__SUPER_ADMIN_TELEGRAM_USER_IDS=123456789,987654321

DATABASE__HOST=postgres
DATABASE__PORT=5432
DATABASE__USER=helpdesk
DATABASE__PASSWORD=helpdesk
DATABASE__DATABASE=helpdesk
DATABASE__ECHO=false

REDIS__HOST=redis
REDIS__PORT=6379
REDIS__DB=0

LOGGING__LEVEL=INFO
LOGGING__STRUCTURED=true
```

Дополнительно для локального Compose:

- `POSTGRES_EXPOSE_PORT`
- `REDIS_EXPOSE_PORT`

## Миграции

Применить все миграции:

```bash
make migrate
```

Создать новую ревизию:

```bash
make make-migration name=add_some_change
```

Проверить, что metadata и миграции согласованы:

```bash
make migration-check
```

Полезные прямые команды Alembic:

```bash
poetry run alembic current
poetry run alembic history
poetry run alembic upgrade head
```

## Тесты и качество

Форматирование:

```bash
make format
```

Линтинг и типы:

```bash
make lint
make typecheck
```

Тесты:

```bash
make test
```

Полный локальный прогон:

```bash
make check
make ci
```

Pre-commit:

```bash
make pre-commit-install
make pre-commit-run
```

## Make-команды

Основные цели `Makefile`:

- `make install` — установить зависимости;
- `make run` — запустить приложение локально;
- `make health` — прогнать bootstrap и readiness;
- `make migrate` — применить миграции;
- `make test` — запустить тесты;
- `make lint` — запустить Ruff и mypy;
- `make check` — локальный quality gate;
- `make ci` — quality gate плюс проверка миграций;
- `make docker-up` / `make docker-down` — управлять Compose stack;
- `make full` — полный Docker happy-path запуск.

Полный список:

```bash
make help
```

## Эксплуатация / диагностика

Операционные точки входа:

```bash
make health
make run
make logs
docker compose ps
```

`/health` доступна операторам и суперадминистраторам и показывает:

- состояние bootstrap;
- доступность PostgreSQL;
- доступность Redis;
- готовность Telegram runtime;
- корректность Redis-backed FSM.

Если приложение не выходит в polling:

- проверьте `BOT__TOKEN`;
- убедитесь, что `APP__DRY_RUN=false`;
- прогоните `make health`.

## Структура проекта

```text
.
├── docker/
├── migrations/
├── src/
│   ├── app/
│   ├── application/
│   ├── bot/
│   │   ├── formatters/
│   │   ├── handlers/
│   │   │   ├── admin/
│   │   │   ├── operator/
│   │   │   └── user/
│   │   ├── keyboards/
│   │   └── texts/
│   ├── domain/
│   └── infrastructure/
├── tests/
├── Makefile
├── docker-compose.yml
├── pyproject.toml
└── README.md
```

## Дальнейшее развитие

Ближайшие безопасные направления развития:

- расширение SLA-автоматизации;
- более глубокая наблюдаемость по runtime и delivery;
- дополнительные сценарии операторской аналитики;
- развитие внутренних application/use-case контрактов без размывания границ слоев.
