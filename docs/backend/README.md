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

## Почему Backend Отделён

- Telegram bot не держит внутри себя продуктовые сценарии;
- transport boundary можно тестировать отдельно;
- развитие архивов, аналитики и export-потоков не ломает presentation слой.
