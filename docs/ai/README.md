# AI

Reliora использует только локальную AI-модель внутри существующего `ai-service`.
Внешние Hugging Face/OpenAI-compatible runtime providers не поддерживаются и не нужны.
`ai-service` остаётся gRPC-сервисом; отдельного HTTP model service нет.

## Возможности

- сводка по заявке;
- черновик ответа оператору;
- подсказки подходящих макросов;
- рекомендация темы при создании обращения;
- анализ тональности клиентского сообщения.

## Конфигурация

Минимальный локальный конфиг:

```dotenv
AI__MODEL_ID=Qwen/Qwen2.5-0.5B-Instruct
AI__LOCAL_MODEL_PATH=
AI__LOCAL_CACHE_DIR=/cache/huggingface
AI__LOCAL_TORCH_CACHE_DIR=/cache/torch
AI__LOCAL_TORCH_KERNEL_CACHE_DIR=/cache/torch_kernels
AI__LOCAL_DEVICE=auto
AI__LOCAL_DTYPE=auto
AI__LOCAL_MAX_INPUT_TOKENS=4096
AI__LOCAL_MAX_CONCURRENT_REQUESTS=1
AI__LOCAL_TOP_P=0.9
AI__LOCAL_REPETITION_PENALTY=1.05
AI__LOCAL_TRUST_REMOTE_CODE=false
```

`AI__MODEL_ID` задаёт Hugging Face model id. Для CPU используйте компактную модель вроде `Qwen/Qwen2.5-0.5B-Instruct`; более крупные модели будут медленнее и могут не поместиться в память.

`AI__LOCAL_MODEL_PATH` задаёт локальный каталог модели. В Docker положите каталог в `models/` и укажите путь вида `/models/qwen`.

Cache volumes сохраняют скачанные веса и Torch kernels между перезапусками. Первый старт может долго скачивать модель.

Операционные настройки генерации:

```dotenv
AI__SUMMARY_TEMPERATURE=0.2
AI__SUMMARY_MAX_OUTPUT_TOKENS=700
AI__REPLY_DRAFT_TEMPERATURE=0.4
AI__REPLY_DRAFT_MAX_OUTPUT_TOKENS=1000
AI__CATEGORY_TEMPERATURE=0.1
AI__CATEGORY_MAX_OUTPUT_TOKENS=400
```

## Запуск и проверка

```bash
make docker-up
make health-ai
make ai-smoke
```

`make health-ai` проверяет gRPC status и факт загрузки модели без генерации. `make ai-smoke` выполняет реальную локальную генерацию сводки и проверяет JSON/schema.

## Диагностика

| Симптом | Что проверить |
| --- | --- |
| model load failed | `make logs-ai`, `AI__MODEL_ID`, доступность сети для первого скачивания |
| model not found | `AI__LOCAL_MODEL_PATH`, наличие каталога внутри `/models` |
| out of memory | уменьшите модель, поставьте `AI__LOCAL_DEVICE=cpu` или настройте GPU |
| invalid JSON | проверьте `make ai-smoke`, уменьшите температуру или увеличьте output tokens |
| медленная генерация | CPU режим может быть медленным; используйте меньшую модель или GPU |

GPU не обязателен. Если среда поддерживает CUDA или MPS, оставьте `AI__LOCAL_DEVICE=auto` или задайте `cuda`, `cuda:0`, `mps`.

## Безопасность

- Не логируйте raw prompt, переписку заявки, внутренние заметки или raw completion.
- Не отправляйте AI-черновик клиенту автоматически.
- Оператор всегда проверяет AI-ответ перед отправкой.
- `AI__LOCAL_TRUST_REMOTE_CODE=true` используйте только для доверенных моделей.
