from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal, Protocol

AIMessageRole = Literal["system", "user"]


@dataclass(slots=True, frozen=True)
class AIMessage:
    role: AIMessageRole
    content: str


class AIProviderError(RuntimeError):
    """Raised when the configured AI provider cannot complete a request."""


class AIProvider(Protocol):
    @property
    def is_enabled(self) -> bool: ...

    @property
    def model_id(self) -> str | None: ...

    async def complete(
        self,
        *,
        messages: Sequence[AIMessage],
        max_output_tokens: int,
        temperature: float,
    ) -> str: ...
