from __future__ import annotations

from .quality_fixtures import AI_QUALITY_FIXTURES


def test_quality_fixture_set_contains_required_cases() -> None:
    assert set(AI_QUALITY_FIXTURES) == {
        "short_ticket_missing_details",
        "angry_customer",
        "attachment_only_ticket",
        "long_conversation",
        "already_resolved_ticket",
        "escalation_required",
        "ambiguous_category",
        "no_prediction_signal",
    }


def test_long_conversation_fixture_exercises_history_cap() -> None:
    fixture = AI_QUALITY_FIXTURES["long_conversation"]

    assert len(fixture.message_history) > 20
    assert fixture.message_history[0].text == "long-history-customer-message-01"
    assert fixture.message_history[-1].text == "long-history-customer-message-25"


def test_no_prediction_signal_fixture_has_categories_without_input_signal() -> None:
    fixture = AI_QUALITY_FIXTURES["no_prediction_signal"]

    assert fixture.category_command().categories
    assert fixture.category_command().text == "   "
    assert fixture.category_command().attachment is None
