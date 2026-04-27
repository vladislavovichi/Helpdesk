from __future__ import annotations

from collections.abc import Sequence

from application.ai.contracts import AIMessage, AIProvider, AIProviderError


class FakeAIProvider(AIProvider):
    def __init__(
        self,
        responses: Sequence[str] = (),
        *,
        enabled: bool = True,
        model_id: str | None = "fake-model",
        raise_error: bool = False,
    ) -> None:
        self.responses = list(responses)
        self._enabled = enabled
        self._model_id = model_id
        self.raise_error = raise_error
        self.calls: list[tuple[Sequence[AIMessage], int, float]] = []

    @property
    def is_enabled(self) -> bool:
        return self._enabled

    @property
    def model_id(self) -> str | None:
        return self._model_id

    @property
    def call_count(self) -> int:
        return len(self.calls)

    @property
    def last_messages(self) -> Sequence[AIMessage]:
        return self.calls[-1][0]

    @property
    def last_prompt(self) -> str:
        return self.last_messages[-1].content

    async def complete(
        self,
        *,
        messages: Sequence[AIMessage],
        max_output_tokens: int,
        temperature: float,
    ) -> str:
        self.calls.append((messages, max_output_tokens, temperature))
        if self.raise_error:
            raise AIProviderError("fake provider failure")
        if not self.responses:
            raise AIProviderError("fake provider has no queued response")
        return self.responses.pop(0)
