from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class AIPredictionConfidence(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    NONE = "none"


@dataclass(slots=True, frozen=True)
class TicketMacroSuggestion:
    macro_id: int
    title: str
    body: str
    reason: str


@dataclass(slots=True, frozen=True)
class TicketAssistSnapshot:
    available: bool
    short_summary: str | None = None
    user_goal: str | None = None
    actions_taken: str | None = None
    current_status: str | None = None
    macro_suggestions: tuple[TicketMacroSuggestion, ...] = ()
    unavailable_reason: str | None = None
    model_id: str | None = None


@dataclass(slots=True, frozen=True)
class TicketCategoryPrediction:
    available: bool
    category_id: int | None = None
    category_code: str | None = None
    category_title: str | None = None
    confidence: AIPredictionConfidence = AIPredictionConfidence.NONE
    reason: str | None = None
    model_id: str | None = None
