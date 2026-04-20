from __future__ import annotations

from application.services.stats import (
    AnalyticsCategorySnapshot,
    AnalyticsOperatorSnapshot,
    AnalyticsRatingBucket,
    AnalyticsWindow,
    HelpdeskAnalyticsSnapshot,
    OperatorTicketLoad,
)
from application.use_cases.analytics.exports import AnalyticsSection
from infrastructure.exports.analytics_snapshot_html import render_analytics_snapshot_html


def test_render_analytics_snapshot_html_contains_svg_charts() -> None:
    snapshot = HelpdeskAnalyticsSnapshot(
        window=AnalyticsWindow.DAYS_7,
        total_open_tickets=8,
        queued_tickets_count=2,
        assigned_tickets_count=4,
        escalated_tickets_count=1,
        closed_tickets_count=11,
        tickets_per_operator=(
            OperatorTicketLoad(operator_id=7, display_name="Иван Петров", ticket_count=3),
            OperatorTicketLoad(operator_id=8, display_name="Анна Смирнова", ticket_count=2),
        ),
        period_created_tickets_count=14,
        period_closed_tickets_count=9,
        average_first_response_time_seconds=420,
        average_resolution_time_seconds=8100,
        satisfaction_average=4.7,
        feedback_count=6,
        feedback_coverage_percent=67,
        rating_distribution=(
            AnalyticsRatingBucket(rating=5, count=4),
            AnalyticsRatingBucket(rating=4, count=2),
        ),
        operator_snapshots=(
            AnalyticsOperatorSnapshot(
                operator_id=7,
                display_name="Иван Петров",
                active_ticket_count=3,
                closed_ticket_count=5,
                average_first_response_time_seconds=360,
                average_resolution_time_seconds=7200,
                average_satisfaction=4.8,
                feedback_count=4,
            ),
        ),
        category_snapshots=(
            AnalyticsCategorySnapshot(
                category_id=2,
                category_title="Доступ и вход",
                created_ticket_count=6,
                open_ticket_count=2,
                closed_ticket_count=4,
                average_satisfaction=4.6,
                feedback_count=3,
                sla_breach_count=1,
            ),
        ),
        best_operators_by_closures=(
            AnalyticsOperatorSnapshot(
                operator_id=7,
                display_name="Иван Петров",
                active_ticket_count=3,
                closed_ticket_count=5,
                average_first_response_time_seconds=360,
                average_resolution_time_seconds=7200,
                average_satisfaction=4.8,
                feedback_count=4,
            ),
        ),
        best_operators_by_satisfaction=(
            AnalyticsOperatorSnapshot(
                operator_id=7,
                display_name="Иван Петров",
                active_ticket_count=3,
                closed_ticket_count=5,
                average_first_response_time_seconds=360,
                average_resolution_time_seconds=7200,
                average_satisfaction=4.8,
                feedback_count=4,
            ),
        ),
        top_categories=(
            AnalyticsCategorySnapshot(
                category_id=2,
                category_title="Доступ и вход",
                created_ticket_count=6,
                open_ticket_count=2,
                closed_ticket_count=4,
                average_satisfaction=4.6,
                feedback_count=3,
                sla_breach_count=1,
            ),
        ),
        first_response_breach_count=1,
        resolution_breach_count=2,
        sla_categories=(
            AnalyticsCategorySnapshot(
                category_id=2,
                category_title="Доступ и вход",
                created_ticket_count=6,
                open_ticket_count=2,
                closed_ticket_count=4,
                average_satisfaction=4.6,
                feedback_count=3,
                sla_breach_count=1,
            ),
        ),
    )

    html = render_analytics_snapshot_html(snapshot, AnalyticsSection.OVERVIEW).decode("utf-8")

    assert "HTML отчёт с графиками" in html
    assert "Статусный портрет" in html
    assert 'class="bar-chart"' in html
    assert 'class="segment-track"' in html
