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
    try:
        raw = await provider.complete(
            messages=(
                AIMessage(role="system", content=instructions),
                AIMessage(role="user", content=prompt),
            ),
            max_output_tokens=max_output_tokens,
            temperature=temperature,
        )
    except AIProviderError:
        return None

    payload = extract_json_object(raw)
    if payload is None:
        return None
    try:
        return schema.model_validate(payload)
    except ValidationError:
        return None


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
