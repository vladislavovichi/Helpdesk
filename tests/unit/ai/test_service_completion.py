from __future__ import annotations

from collections.abc import Sequence

from pydantic import BaseModel

from ai_service.service_completion import complete_json
from application.ai.contracts import AIMessage, AIProvider


class Payload(BaseModel):
    value: str


class SequencedProvider(AIProvider):
    def __init__(self, responses: Sequence[str]) -> None:
        self.responses = list(responses)
        self.calls: list[tuple[Sequence[AIMessage], int, float]] = []

    @property
    def is_enabled(self) -> bool:
        return True

    @property
    def model_id(self) -> str | None:
        return "test-model"

    async def complete(
        self,
        *,
        messages: Sequence[AIMessage],
        max_output_tokens: int,
        temperature: float,
    ) -> str:
        self.calls.append((messages, max_output_tokens, temperature))
        return self.responses.pop(0)


async def test_complete_json_retries_once_after_invalid_json_and_returns_valid_payload() -> None:
    provider = SequencedProvider(("not json", '{"value":"ok"}'))

    result = await complete_json(
        provider=provider,
        instructions="Return JSON.",
        prompt='Expected: {"value":"..."}',
        schema=Payload,
        max_output_tokens=80,
        temperature=0,
    )

    assert result == Payload(value="ok")
    assert len(provider.calls) == 2
    assert "strictly valid JSON" in provider.calls[1][0][1].content


async def test_complete_json_performs_only_one_retry() -> None:
    provider = SequencedProvider(("not json", "still not json", '{"value":"late"}'))

    result = await complete_json(
        provider=provider,
        instructions="Return JSON.",
        prompt='Expected: {"value":"..."}',
        schema=Payload,
        max_output_tokens=80,
        temperature=0,
    )

    assert result is None
    assert len(provider.calls) == 2
