from __future__ import annotations

import csv
from io import StringIO

from application.services.stats import HelpdeskAnalyticsSnapshot, get_analytics_window_label
from application.use_cases.analytics.exports import AnalyticsSection, get_analytics_section_label

FIELDNAMES = ("section", "window", "block", "metric_key", "metric_label", "value")


def render_analytics_snapshot_csv(
    snapshot: HelpdeskAnalyticsSnapshot,
    section: AnalyticsSection,
) -> bytes:
    buffer = StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=FIELDNAMES)
    writer.writeheader()

    for block, metric_key, metric_label, value in _build_rows(snapshot, section):
        writer.writerow(
            {
                "section": get_analytics_section_label(section),
                "window": get_analytics_window_label(snapshot.window),
                "block": block,
                "metric_key": metric_key,
                "metric_label": metric_label,
                "value": value,
            }
        )

    return buffer.getvalue().encode("utf-8-sig")


def _build_rows(
    snapshot: HelpdeskAnalyticsSnapshot,
    section: AnalyticsSection,
) -> tuple[tuple[str, str, str, str | int | float], ...]:
    rows: list[tuple[str, str, str, str | int | float]] = []

    rows.extend(
        (
            ("Сводка", "total_open_tickets", "Открытые", snapshot.total_open_tickets),
            ("Сводка", "queued_tickets_count", "В очереди", snapshot.queued_tickets_count),
            ("Сводка", "assigned_tickets_count", "В работе", snapshot.assigned_tickets_count),
            ("Сводка", "escalated_tickets_count", "Эскалация", snapshot.escalated_tickets_count),
            ("Сводка", "closed_tickets_count", "Закрытые", snapshot.closed_tickets_count),
            (
                "Период",
                "period_created_tickets_count",
                "Новые за период",
                snapshot.period_created_tickets_count,
            ),
            (
                "Период",
                "period_closed_tickets_count",
                "Закрыто за период",
                snapshot.period_closed_tickets_count,
            ),
            ("Период", "feedback_count", "Оценок", snapshot.feedback_count),
        )
    )

    if section in {AnalyticsSection.OVERVIEW, AnalyticsSection.OPERATORS}:
        for index, load in enumerate(snapshot.tickets_per_operator, start=1):
            rows.append(
                (
                    "Нагрузка",
                    f"operator_load_{index}",
                    load.display_name,
                    load.ticket_count,
                )
            )
        for index, operator_snapshot in enumerate(snapshot.best_operators_by_closures, start=1):
            rows.append(
                (
                    "Закрытия",
                    f"operator_closures_{index}",
                    operator_snapshot.display_name,
                    operator_snapshot.closed_ticket_count,
                )
            )

    if section in {AnalyticsSection.OVERVIEW, AnalyticsSection.TOPICS, AnalyticsSection.SLA}:
        for index, category_snapshot in enumerate(snapshot.top_categories, start=1):
            rows.append(
                (
                    "Темы",
                    f"top_category_{index}",
                    category_snapshot.category_title,
                    category_snapshot.created_ticket_count,
                )
            )

    if section in {AnalyticsSection.QUALITY, AnalyticsSection.OVERVIEW}:
        for rating_bucket in snapshot.rating_distribution:
            rows.append(
                (
                    "Оценки",
                    f"rating_{rating_bucket.rating}",
                    f"Оценка {rating_bucket.rating}",
                    rating_bucket.count,
                )
            )

    if section == AnalyticsSection.SLA:
        rows.extend(
            (
                (
                    "SLA",
                    "first_response_breach_count",
                    "Нарушения первого ответа",
                    snapshot.first_response_breach_count,
                ),
                (
                    "SLA",
                    "resolution_breach_count",
                    "Нарушения решения",
                    snapshot.resolution_breach_count,
                ),
            )
        )
        for index, sla_category in enumerate(snapshot.sla_categories, start=1):
            rows.append(
                (
                    "SLA по темам",
                    f"sla_category_{index}",
                    sla_category.category_title,
                    sla_category.sla_breach_count,
                )
            )

    return tuple(rows)
