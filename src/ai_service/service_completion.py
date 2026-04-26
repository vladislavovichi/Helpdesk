from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, ValidationError

from application.ai.contracts import AIMessage, AIProvider, AIProviderError


async def complete_json[SchemaT: BaseModel](
    *,
    provider: AIProvider,
    instructions: str,
    prompt: str,
    schema: type[SchemaT],
    max_output_tokens: int,
    temperature: float,
) -> SchemaT | None:
    messages = (
        AIMessage(role="system", content=instructions),
        AIMessage(role="user", content=prompt),
    )
    try:
        raw = await provider.complete(
            messages=messages,
            max_output_tokens=max_output_tokens,
            temperature=temperature,
        )
    except AIProviderError:
        return None

    result = _validate_json_payload(raw=raw, schema=schema)
    if result is not None:
        return result

    retry_prompt = build_json_retry_prompt(prompt=prompt, schema=schema)
    try:
        retry_raw = await provider.complete(
            messages=(
                AIMessage(role="system", content=instructions),
                AIMessage(role="user", content=retry_prompt),
            ),
            max_output_tokens=max_output_tokens,
            temperature=temperature,
        )
    except AIProviderError:
        return None

    return _validate_json_payload(raw=retry_raw, schema=schema)


def _validate_json_payload[SchemaT: BaseModel](
    *,
    raw: str,
    schema: type[SchemaT],
) -> SchemaT | None:
    payload = extract_json_object(raw)
    if payload is None:
        return None
    try:
        return schema.model_validate(payload)
    except ValidationError:
        return None


def build_json_retry_prompt(*, prompt: str, schema: type[BaseModel]) -> str:
    return "\n".join(
        [
            prompt,
            "",
            "Предыдущий ответ не был валидным JSON для ожидаемой структуры.",
            "Return strictly valid JSON only, with no markdown and no surrounding explanation.",
            "Верни строго валидный JSON-объект без markdown, комментариев и пояснений вокруг.",
            "Структура должна соответствовать этой JSON Schema:",
            json.dumps(schema.model_json_schema(), ensure_ascii=False),
        ]
    )


def extract_json_object(raw: str) -> dict[str, Any] | None:
    text = raw.strip()
    if not text:
        return None
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start < 0 or end <= start:
            return None
        try:
            parsed = json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            return None
    return parsed if isinstance(parsed, dict) else None
