# Backup И Restore PostgreSQL

## Что Попадает В Backup

`make backup-db` делает логический backup PostgreSQL через `pg_dump -Fc`.

В backup попадает всё, что живёт в PostgreSQL:

- заявки и история;
- операторы, роли и invite-данные;
- категории, макросы, теги;
- feedback;
- audit trail;
- AI summary cache и прочие таблицы приложения.

## Что Не Попадает

Не попадает:

- Redis runtime-state;
- локальные файлы в `assets/`, если они существуют вне PostgreSQL;
- Docker images и compose-конфигурация;
- `.env`.

Backup БД не восстанавливает весь runtime-узел целиком.

## Как Сделать Backup

```bash
make backup-db
```

По умолчанию файл создаётся в `backups/postgres/` с UTC timestamp в имени.

Если нужен явный путь:

```bash
BACKUP_PATH=backups/postgres/release-2026-04-13.dump make backup-db
```

## Как Восстановить

```bash
BACKUP_PATH=backups/postgres/helpdesk_20260413T120000Z.dump make restore-db
```

Restore использует `pg_restore --clean --if-exists`, поэтому он перезаписывает объекты в целевой базе. Это не команда “на всякий случай”. Её нужно выполнять только осознанно.

## Практические Осторожности

- перед restore остановите пользовательскую активность или хотя бы предупредите команду;
- убедитесь, что восстанавливаете backup в правильное окружение;
- после restore обязательно выполните `make smoke`;
- если restore делается после неудачного релиза, отдельно проверьте совместимость кода и схемы.

## Минимальная Проверка После Restore

```bash
make health
make smoke
```

Если smoke-check проходит, значит стек снова видит БД, Redis, backend, `ai-service` и bot runtime dependencies.
