# Backend И gRPC

## Что Здесь Живёт

- protobuf-контракты в `src/backend/proto`;
- gRPC client/server/translators в `src/backend/grpc`;
- backend runtime в `src/backend/main.py`;
- service composition через `application.services.helpdesk`.

## Основные Backend Surface'ы

- ticket details и operator workflows;
- queue и operator ticket lists;
- archived ticket list;
- ticket report export `CSV` / `HTML`;
- analytics snapshot и analytics export `CSV` / `HTML`.

## Принцип Работы

- gRPC server принимает transport request;
- translator переводит transport в application-модель;
- `HelpdeskService` вызывает use case;
- результат сериализуется обратно в protobuf.

## Internal Security

Внутренний transport теперь требует явную auth metadata:

- token берётся из `BACKEND_AUTH__TOKEN`;
- caller name задаётся через `BACKEND_AUTH__CALLER`;
- каждый запрос несёт `x-correlation-id`;
- actor id дополнительно прокидывается metadata-слоем для audit и trace, даже там, где protobuf request не содержит `actor`.

Backend валидирует metadata до входа в бизнес-логику и отклоняет неавторизованные вызовы.

## Наблюдаемость

gRPC runtime пишет более полезные structured logs:

- request started / completed;
- caller, peer, actor id и correlation id;
- failure category и duration;
- transport-level denials без Telegram-facing утечки деталей.

Для read-only вызовов client использует узкий retry/backoff на `UNAVAILABLE` и `DEADLINE_EXCEEDED`.

## Почему Backend Отделён

- Telegram bot не держит внутри себя продуктовые сценарии;
- transport boundary можно тестировать отдельно;
- развитие архивов, аналитики и export-потоков не ломает presentation слой.
