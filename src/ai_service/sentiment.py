from __future__ import annotations

import re
from collections.abc import Sequence

from application.contracts.ai import (
    AIContextMessage,
    AnalyzedTicketSentimentResult,
    AnalyzeTicketSentimentCommand,
)
from domain.enums.tickets import TicketMessageSenderType, TicketSentiment, TicketSignalConfidence

SENTIMENT_MODEL_ID = "sentiment-heuristic-v1"
TEXT_SIGNAL_RE = re.compile(r"[^\W\d_]", re.UNICODE)
REPEATED_PUNCTUATION_RE = re.compile(r"[!?]{3,}")
STRONG_ESCALATION_PHRASES = (
    "жалоба",
    "претенз",
    "в суд",
    "роспотребнадзор",
    "прокуратур",
    "верните деньги",
    "безобраз",
    "недопустимо",
    "это неприемлемо",
    "ужасный сервис",
    "полный игнор",
    "сейчас же",
    "немедленно",
)
FRUSTRATION_PHRASES = (
    "до сих пор",
    "уже который",
    "уже второй",
    "уже третий",
    "сколько можно",
    "где ответ",
    "почему не отвечаете",
    "почему молчите",
    "не отвечаете",
    "игнорируете",
    "никакой реакции",
    "снова",
    "опять",
    "срочно",
    "очень срочно",
    "ау",
)
PROFANITY_MARKERS = (
    "идиот",
    "бред",
    "кошмар",
    "ужас",
    "отврат",
    "бездар",
    "хам",
)


def analyze_ticket_sentiment(
    command: AnalyzeTicketSentimentCommand,
) -> AnalyzedTicketSentimentResult:
    normalized = normalize_sentiment_text(command.text)
    if normalized is None:
        return AnalyzedTicketSentimentResult(
            available=False,
            model_id=SENTIMENT_MODEL_ID,
        )

    strong_hits = count_phrase_hits(normalized, STRONG_ESCALATION_PHRASES)
    frustration_hits = count_phrase_hits(normalized, FRUSTRATION_PHRASES)
    profanity_hits = count_phrase_hits(normalized, PROFANITY_MARKERS)
    punctuation_signal = 1 if REPEATED_PUNCTUATION_RE.search(command.text or "") else 0
    uppercase_signal = 1 if has_excessive_uppercase(command.text) else 0
    unanswered_streak = recent_unanswered_client_streak(command.recent_messages)
    follow_up_signal = (
        1 if unanswered_streak >= 2 and (frustration_hits > 0 or punctuation_signal) else 0
    )

    weighted_score = (
        (strong_hits * 3)
        + (profanity_hits * 3)
        + (frustration_hits * 2)
        + punctuation_signal
        + uppercase_signal
        + follow_up_signal
    )

    if strong_hits > 0 or profanity_hits > 0:
        confidence = (
            TicketSignalConfidence.HIGH
            if strong_hits + profanity_hits >= 2 or uppercase_signal
            else TicketSignalConfidence.MEDIUM
        )
        return AnalyzedTicketSentimentResult(
            available=True,
            sentiment=TicketSentiment.ESCALATION_RISK,
            confidence=confidence,
            reason="Резкие формулировки и требование немедленной реакции.",
            model_id=SENTIMENT_MODEL_ID,
        )

    if weighted_score >= 5:
        return AnalyzedTicketSentimentResult(
            available=True,
            sentiment=TicketSentiment.ESCALATION_RISK,
            confidence=TicketSignalConfidence.MEDIUM,
            reason="Накопились признаки сильного раздражения и давления на ответ.",
            model_id=SENTIMENT_MODEL_ID,
        )

    if weighted_score >= 3 or (frustration_hits > 0 and punctuation_signal > 0):
        return AnalyzedTicketSentimentResult(
            available=True,
            sentiment=TicketSentiment.FRUSTRATED,
            confidence=(
                TicketSignalConfidence.HIGH
                if weighted_score >= 5
                else TicketSignalConfidence.MEDIUM
            ),
            reason="Есть признаки раздражения и нетерпения в сообщении.",
            model_id=SENTIMENT_MODEL_ID,
        )

    return AnalyzedTicketSentimentResult(
        available=True,
        sentiment=TicketSentiment.CALM,
        confidence=TicketSignalConfidence.MEDIUM,
        reason="Сообщение описывает ситуацию без явной эскалации.",
        model_id=SENTIMENT_MODEL_ID,
    )


def normalize_sentiment_text(text: str | None) -> str | None:
    if text is None:
        return None
    normalized = " ".join(text.lower().replace("ё", "е").split())
    if not normalized:
        return None
    if not TEXT_SIGNAL_RE.search(normalized):
        return normalized
    return normalized


def count_phrase_hits(text: str, phrases: Sequence[str]) -> int:
    return sum(1 for phrase in phrases if phrase in text)


def has_excessive_uppercase(text: str | None) -> bool:
    if text is None:
        return False
    letters = [char for char in text if char.isalpha()]
    if len(letters) < 8:
        return False
    uppercase_letters = sum(1 for char in letters if char.isupper())
    return uppercase_letters / len(letters) >= 0.5


def recent_unanswered_client_streak(messages: Sequence[AIContextMessage]) -> int:
    streak = 0
    for message in reversed(messages):
        if message.sender_type != TicketMessageSenderType.CLIENT:
            break
        streak += 1
    return streak
