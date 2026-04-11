# Разработка

## Базовый Локальный Цикл

```bash
cp .env.example .env
make install
make migrate
make run-backend
make run-bot
```

## Качество

```bash
make format
make lint
make typecheck
make test
make check
```

## Что Важно Не Ломать

- gRPC extraction и transport contracts;
- roles и authorization;
- queue pagination;
- live dialogue;
- categories, feedback, exports, analytics;
- attachments и internal notes;
- button-first premium UX.

## Рекомендованный Подход К Изменениям

- бизнес-логику добавлять в `application` и `infrastructure`;
- handlers держать тонкими;
- тексты — в `bot/texts`;
- клавиатуры — в `bot/keyboards`;
- форматирование — в `bot/formatters`;
- рендеринг export'ов — в `infrastructure/exports`.
