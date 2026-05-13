from collections.abc import Sequence
from datetime import UTC, datetime

from application.services.stats import HelpdeskAnalyticsSnapshot, get_analytics_window_label
from application.use_cases.analytics.exports import AnalyticsSection, get_analytics_section_label
from infrastructure.exports.html_templates import render_html_template


def render_analytics_snapshot_html(
    snapshot: HelpdeskAnalyticsSnapshot,
    section: AnalyticsSection,
) -> bytes:
    title = get_analytics_section_label(section)
    generated_at = datetime.now(UTC).strftime("%d.%m.%Y %H:%M UTC")
    window_label = get_analytics_window_label(snapshot.window)
    html = render_html_template(
        "analytics_snapshot.html.j2",
        {
            "css": _DOCUMENT_CSS,
            "title": title,
            "generated_at": generated_at,
            "window_label": window_label,
            "hero_copy": _hero_copy(section),
            "insight_title": _section_insight_title(section),
            "cover_metrics": _cover_metrics(snapshot),
            "stat_cards": _stat_cards(snapshot),
            "section_metrics": _section_metrics(snapshot, section),
            "charts": _charts(snapshot, section),
        },
    )
    return html.encode("utf-8")


_DOCUMENT_CSS = """
    :root {
      color-scheme: light;
      --bg: #f3eee7;
      --paper: rgba(255, 255, 255, 0.86);
      --paper-strong: #fffdf9;
      --surface: rgba(255, 255, 255, 0.72);
      --surface-muted: rgba(248, 243, 237, 0.82);
      --line: rgba(38, 45, 53, 0.09);
      --line-strong: rgba(38, 45, 53, 0.16);
      --text: #1b222b;
      --muted: #66727d;
      --accent: #1f2834;
      --accent-soft: rgba(31, 40, 52, 0.07);
      --success: #315b4b;
      --warning: #8a6229;
      --danger: #8c3f3f;
      --info: #405d73;
      --shadow-sm: 0 8px 18px rgba(26, 33, 41, 0.05);
      --shadow-md: 0 18px 42px rgba(26, 33, 41, 0.08);
      --shadow-lg: 0 32px 84px rgba(26, 33, 41, 0.12);
      --radius-sm: 10px;
      --radius-md: 16px;
      --radius-lg: 22px;
      --radius-xl: 34px;
    }
    * { box-sizing: border-box; }
    html { background: #e5dbcf; }
    body {
      margin: 0;
      min-width: 0;
      background:
        radial-gradient(circle at 10% -6%, rgba(180, 151, 110, 0.24), transparent 34%),
        radial-gradient(circle at 94% 2%, rgba(64, 93, 115, 0.14), transparent 30%),
        radial-gradient(circle at 50% 104%, rgba(255, 255, 255, 0.88), transparent 40%),
        linear-gradient(180deg, #fbf8f3 0%, var(--bg) 54%, #e5dbcf 100%);
      color: var(--text);
      font-family: "SF Pro Text", "Inter", "Segoe UI", system-ui, sans-serif;
      line-height: 1.6;
      padding: 32px 16px 54px;
    }
    .page { width: min(1180px, 100%); margin: 0 auto; }
    .cover, .stat-card, .chart-card, .report-section {
      border: 1px solid var(--line);
      background: var(--paper);
      box-shadow: var(--shadow-sm);
    }
    .cover {
      overflow: hidden;
      border-color: rgba(255, 255, 255, 0.74);
      border-radius: var(--radius-xl);
      background:
        radial-gradient(circle at top right, rgba(31, 40, 52, 0.08), transparent 38%),
        linear-gradient(135deg, rgba(255, 255, 255, 0.96), rgba(243, 235, 225, 0.82));
      box-shadow: var(--shadow-lg);
      padding: 34px;
      margin-bottom: 18px;
    }
    .cover-grid {
      display: grid;
      grid-template-columns: minmax(0, 1.35fr) minmax(300px, 0.85fr);
      gap: 28px;
      align-items: start;
    }
    .eyebrow {
      margin: 0 0 10px;
      color: #756249;
      font-size: 12px;
      font-weight: 760;
      text-transform: uppercase;
    }
    h1, h2, h3 {
      margin: 0;
      color: var(--text);
      font-weight: 680;
      line-height: 1.08;
      letter-spacing: 0;
    }
    h1 { font-size: clamp(34px, 5vw, 56px); }
    h2 { font-size: 24px; }
    .hero-copy {
      max-width: 780px;
      margin: 14px 0 0;
      color: #3c4652;
      font-size: 18px;
      line-height: 1.56;
      overflow-wrap: anywhere;
    }
    .chip-row {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-top: 22px;
    }
    .chip {
      display: inline-flex;
      align-items: center;
      max-width: 100%;
      min-height: 32px;
      padding: 7px 12px;
      border: 1px solid rgba(38, 45, 53, 0.08);
      border-radius: 999px;
      background: rgba(255, 255, 255, 0.62);
      color: #4b5662;
      font-size: 13px;
      font-weight: 680;
      overflow-wrap: anywhere;
    }
    .cover-aside {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 12px;
      padding: 18px;
      border: 1px solid var(--line);
      border-radius: var(--radius-lg);
      background: rgba(255, 255, 255, 0.58);
    }
    .cover-metric, .stat-card {
      min-width: 0;
      padding: 16px;
      border-radius: var(--radius-md);
      background: rgba(255, 255, 255, 0.66);
    }
    .cover-label, .stat-label, .metric-label {
      color: var(--muted);
      font-size: 12px;
      font-weight: 720;
      text-transform: uppercase;
    }
    .cover-value, .stat-value {
      margin-top: 4px;
      color: var(--text);
      font-size: 24px;
      font-weight: 760;
      line-height: 1.1;
      overflow-wrap: anywhere;
    }
    .stat-note {
      margin-top: 6px;
      color: var(--muted);
      font-size: 13px;
    }
    .kpi-board {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
      gap: 12px;
      margin-bottom: 18px;
    }
    .report-section, .chart-card {
      border-radius: var(--radius-xl);
      padding: 24px;
      margin-bottom: 16px;
    }
    .section-head {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 18px;
      margin-bottom: 18px;
    }
    .metrics {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
      gap: 10px;
    }
    .metric-row {
      display: grid;
      gap: 5px;
      min-width: 0;
      padding: 14px;
      border: 1px solid var(--line);
      border-radius: var(--radius-md);
      background: rgba(255, 255, 255, 0.62);
    }
    .metric-value {
      font-weight: 760;
      overflow-wrap: anywhere;
    }
    .charts-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(330px, 1fr));
      gap: 16px;
    }
    .chart-card h2 { margin-bottom: 8px; }
    .chart-note {
      margin-bottom: 14px;
      color: var(--muted);
      font-size: 14px;
    }
    .chart-body, .bar-chart, .segment-legend {
      display: grid;
      gap: 12px;
    }
    .segment-track {
      display: flex;
      min-height: 18px;
      overflow: hidden;
      border-radius: 999px;
      background: #e8dfd3;
    }
    .segment-fill { min-width: 10px; }
    .legend-row, .bar-head {
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 14px;
      align-items: baseline;
    }
    .legend-label, .bar-label {
      color: var(--text);
      overflow-wrap: anywhere;
    }
    .legend-value, .bar-value {
      color: var(--muted);
      font-size: 13px;
      text-align: right;
      white-space: nowrap;
    }
    .bar-row { display: grid; gap: 7px; }
    .bar-track {
      height: 11px;
      overflow: hidden;
      border-radius: 999px;
      background: #e8dfd3;
    }
    .bar-fill {
      height: 100%;
      min-width: 8px;
      border-radius: 999px;
    }
    .empty-state {
      padding: 18px;
      border: 1px dashed var(--line-strong);
      border-radius: var(--radius-lg);
      background: var(--surface-muted);
      color: var(--muted);
    }
    .report-footer {
      display: flex;
      flex-wrap: wrap;
      justify-content: space-between;
      gap: 10px 18px;
      padding: 18px 4px 0;
      color: var(--muted);
      font-size: 12px;
    }
    @media (max-width: 760px) {
      body { padding: 18px 12px 34px; }
      .cover, .report-section, .chart-card { padding: 22px; border-radius: 24px; }
      .cover-grid, .section-head { grid-template-columns: 1fr; flex-direction: column; }
      .cover-grid { display: grid; }
      .cover-aside { grid-template-columns: 1fr; }
      .kpi-board { grid-template-columns: repeat(auto-fit, minmax(145px, 1fr)); }
      .charts-grid { grid-template-columns: 1fr; }
      h1 { font-size: 32px; }
      h2 { font-size: 22px; }
      .hero-copy { font-size: 16px; }
      .legend-row, .bar-head { grid-template-columns: 1fr; gap: 3px; }
      .legend-value, .bar-value { text-align: left; }
    }
    @media (max-width: 390px) {
      body { padding-inline: 10px; }
      .cover, .report-section, .chart-card { padding: 18px; }
      .kpi-board, .metrics { grid-template-columns: 1fr; }
      .chip { white-space: normal; }
    }
    @page { margin: 16mm; }
    @media print {
      html, body { background: #fff !important; }
      body { padding: 0; color: #111827; font-size: 11pt; }
      .cover, .stat-card, .chart-card, .report-section, .metric-row, .cover-metric {
        box-shadow: none !important;
        background: #fff !important;
        border-color: #d6d3ce !important;
      }
      .cover, .report-section, .chart-card, .stat-card, .metric-row {
        page-break-inside: avoid;
        break-inside: avoid;
      }
      .report-footer { border-top: 1px solid #d6d3ce; margin-top: 10mm; }
    }
"""


def _hero_copy(section: AnalyticsSection) -> str:
    messages = {
        AnalyticsSection.OVERVIEW: (
            "Спокойный снимок по потоку заявок, качеству сервиса и рабочей нагрузке команды."
        ),
        AnalyticsSection.OPERATORS: (
            "Фокус на распределении нагрузки, закрытиях и качестве ответов по операторам."
        ),
        AnalyticsSection.TOPICS: (
            "Темы обращений, их объём и где именно сосредоточен продуктовый спрос."
        ),
        AnalyticsSection.QUALITY: "Качество поддержки, клиентская оценка и глубина обратной связи.",
        AnalyticsSection.SLA: (
            "Где появляются нарушения SLA и какие направления требуют раннего внимания."
        ),
    }
    return messages[section]


def _section_insight_title(section: AnalyticsSection) -> str:
    return {
        AnalyticsSection.OVERVIEW: "Ключевые показатели",
        AnalyticsSection.OPERATORS: "Операторская картина",
        AnalyticsSection.TOPICS: "Темы и спрос",
        AnalyticsSection.QUALITY: "Качество сервиса",
        AnalyticsSection.SLA: "SLA и риски",
    }[section]


def _cover_metrics(snapshot: HelpdeskAnalyticsSnapshot) -> list[dict[str, object]]:
    return [
        {"label": "Открыто", "value": snapshot.total_open_tickets},
        {"label": "Создано", "value": snapshot.period_created_tickets_count},
        {"label": "Закрыто", "value": snapshot.period_closed_tickets_count},
        {"label": "Оценка", "value": _format_rating(snapshot.satisfaction_average)},
        {"label": "Покрытие", "value": _format_percent(snapshot.feedback_coverage_percent)},
    ]


def _stat_cards(snapshot: HelpdeskAnalyticsSnapshot) -> list[dict[str, object]]:
    return [
        {
            "label": "Открыто",
            "value": snapshot.total_open_tickets,
            "note": "Все незакрытые заявки",
        },
        {
            "label": "В очереди",
            "value": snapshot.queued_tickets_count,
            "note": "Ожидают назначения",
        },
        {
            "label": "В работе",
            "value": snapshot.assigned_tickets_count,
            "note": "Назначены операторам",
        },
        {
            "label": "Эскалации",
            "value": snapshot.escalated_tickets_count,
            "note": "Требуют внимания",
        },
        {
            "label": "Закрыто всего",
            "value": snapshot.closed_tickets_count,
            "note": "Исторически закрытые",
        },
        {
            "label": "Создано",
            "value": snapshot.period_created_tickets_count,
            "note": "За выбранный период",
        },
        {
            "label": "Закрыто",
            "value": snapshot.period_closed_tickets_count,
            "note": "За выбранный период",
        },
        {
            "label": "Первый ответ",
            "value": _format_duration(snapshot.average_first_response_time_seconds),
            "note": "Среднее время",
        },
        {
            "label": "Решение",
            "value": _format_duration(snapshot.average_resolution_time_seconds),
            "note": "Среднее время",
        },
        {
            "label": "Satisfaction",
            "value": _format_rating(snapshot.satisfaction_average),
            "note": "Средняя оценка",
        },
        {"label": "Feedback", "value": snapshot.feedback_count, "note": "Количество оценок"},
        {
            "label": "Coverage",
            "value": _format_percent(snapshot.feedback_coverage_percent),
            "note": "Покрытие отзывами",
        },
    ]


def _charts(
    snapshot: HelpdeskAnalyticsSnapshot,
    section: AnalyticsSection,
) -> list[dict[str, object]]:
    return [
        _status_mix_chart(snapshot),
        _volume_chart(snapshot),
        _category_chart(snapshot, section),
        _quality_chart(snapshot, section),
        _operator_chart(snapshot, section),
    ]


def _status_mix_chart(snapshot: HelpdeskAnalyticsSnapshot) -> dict[str, object]:
    items = (
        ("В очереди", snapshot.queued_tickets_count, "#8a6229"),
        ("В работе", snapshot.assigned_tickets_count, "#405d73"),
        ("Эскалация", snapshot.escalated_tickets_count, "#8c3f3f"),
        ("Закрытые", snapshot.closed_tickets_count, "#315b4b"),
    )
    total = sum(value for _, value, _ in items)
    chart_total = total or 1
    segments = [
        {"width": _segment_width(value, chart_total), "color": color}
        for _, value, color in items
        if value > 0
    ] or [{"width": 100, "color": "#d8d0c5"}]
    legend = [
        {
            "label": label,
            "value": f"{value} · {_format_percent(round((value / chart_total) * 100))}",
        }
        for label, value, _ in items
    ]
    return {
        "kind": "status_mix",
        "title": "Статусный портрет",
        "note": "Распределение текущей базы заявок по ключевым статусам.",
        "total": total,
        "segments": segments,
        "legend": legend,
    }


def _volume_chart(snapshot: HelpdeskAnalyticsSnapshot) -> dict[str, object]:
    return {
        "kind": "bar",
        "title": "Объём периода",
        "note": "Сравнение входящего потока и закрытых дел за выбранное окно.",
        "rows": _dual_bar_rows(
            items=(
                ("Создано", snapshot.period_created_tickets_count, "#405d73"),
                ("Закрыто", snapshot.period_closed_tickets_count, "#315b4b"),
            )
        ),
    }


def _category_chart(
    snapshot: HelpdeskAnalyticsSnapshot,
    section: AnalyticsSection,
) -> dict[str, object]:
    items: Sequence[tuple[str | None, int | float]]
    if section == AnalyticsSection.SLA:
        items = [
            (item.category_title, item.sla_breach_count) for item in snapshot.sla_categories[:5]
        ]
        title = "Нарушения по темам"
        note = "Где SLA проседает сильнее всего."
        color = "#8c3f3f"
    else:
        items = [
            (item.category_title, item.created_ticket_count) for item in snapshot.top_categories[:5]
        ]
        title = "Топ тем"
        note = "Самые заметные направления входящего потока."
        color = "#405d73"
    return {"kind": "bar", "title": title, "note": note, "rows": _bar_rows(items, color=color)}


def _quality_chart(
    snapshot: HelpdeskAnalyticsSnapshot,
    section: AnalyticsSection,
) -> dict[str, object]:
    items: Sequence[tuple[str | None, int | float]]
    if section == AnalyticsSection.SLA:
        items = [
            ("Первый ответ", snapshot.first_response_breach_count),
            ("Решение", snapshot.resolution_breach_count),
        ]
        title = "Срез SLA"
        note = "Разделение нарушений по типу."
        color = "#8c3f3f"
    else:
        items = tuple(
            (f"Оценка {item.rating}", item.count) for item in snapshot.rating_distribution
        )
        title = "Распределение оценок"
        note = "Как клиенты оценивали поддержку."
        color = "#8a6229"
    return {"kind": "bar", "title": title, "note": note, "rows": _bar_rows(items[:5], color=color)}


def _operator_chart(
    snapshot: HelpdeskAnalyticsSnapshot,
    section: AnalyticsSection,
) -> dict[str, object]:
    items: Sequence[tuple[str | None, int | float]]
    if section == AnalyticsSection.OPERATORS:
        items = [
            (item.display_name, item.closed_ticket_count)
            for item in snapshot.best_operators_by_closures[:5]
        ]
        title = "Закрытия по операторам"
        note = "Кто дал основной результат за период."
        color = "#405d73"
    elif section == AnalyticsSection.QUALITY:
        items = [
            (item.display_name, _format_float(item.average_satisfaction))
            for item in snapshot.best_operators_by_satisfaction[:5]
        ]
        title = "Лидеры по качеству"
        note = "Операторы с лучшей клиентской оценкой."
        color = "#315b4b"
    else:
        items = [
            (item.display_name, item.ticket_count) for item in snapshot.tickets_per_operator[:5]
        ]
        title = "Текущая нагрузка"
        note = "Сколько активных дел сейчас у каждого оператора."
        color = "#405d73"
    return {"kind": "bar", "title": title, "note": note, "rows": _bar_rows(items, color=color)}


def _dual_bar_rows(items: Sequence[tuple[str, int, str]]) -> list[dict[str, object]]:
    max_value = max((value for _, value, _ in items), default=1) or 1
    return [
        {
            "label": label,
            "value": str(value),
            "width": _bar_width(round((value / max_value) * 100, 2), value) if value > 0 else 0,
            "color": color,
        }
        for label, value, color in items
    ]


def _bar_rows(
    items: Sequence[tuple[str | None, int | float]],
    *,
    color: str,
) -> list[dict[str, object]]:
    normalized_items = [
        ((label or "Без названия"), _coerce_numeric(value))
        for label, value in items
        if _coerce_numeric(value) > 0
    ]
    if not normalized_items:
        return []
    max_value = max(value for _, value in normalized_items) or 1
    return [
        {
            "label": _truncate(label, 64),
            "value": _format_chart_value(value),
            "width": max(round((value / max_value) * 100, 2), 3),
            "color": color,
        }
        for label, value in normalized_items
    ]


def _section_metrics(
    snapshot: HelpdeskAnalyticsSnapshot,
    section: AnalyticsSection,
) -> list[dict[str, object]]:
    if section == AnalyticsSection.OPERATORS:
        rows = [
            (
                "Активных назначений",
                sum(item.ticket_count for item in snapshot.tickets_per_operator),
            ),
            ("Лучший по закрытиям", _top_operator_by_closures(snapshot)),
            ("Лучший по качеству", _top_operator_by_quality(snapshot)),
            (
                "Средний первый ответ",
                _format_duration(snapshot.average_first_response_time_seconds),
            ),
            ("Среднее решение", _format_duration(snapshot.average_resolution_time_seconds)),
        ]
    elif section == AnalyticsSection.TOPICS:
        rows = [
            ("Самая активная тема", _top_category(snapshot)),
            (
                "Открытых по темам",
                sum(item.open_ticket_count for item in snapshot.category_snapshots),
            ),
            (
                "Закрыто по темам",
                sum(item.closed_ticket_count for item in snapshot.category_snapshots),
            ),
            ("Лучшая тема по качеству", _best_quality_category(snapshot)),
        ]
    elif section == AnalyticsSection.QUALITY:
        rows = [
            ("Средний рейтинг", _format_rating(snapshot.satisfaction_average)),
            ("Оценок", str(snapshot.feedback_count)),
            ("Покрытие", _format_percent(snapshot.feedback_coverage_percent)),
            ("Лучший оператор", _top_operator_by_quality(snapshot)),
            ("Лучшая тема", _best_quality_category(snapshot)),
        ]
    elif section == AnalyticsSection.SLA:
        rows = [
            ("Нарушения первого ответа", str(snapshot.first_response_breach_count)),
            ("Нарушения решения", str(snapshot.resolution_breach_count)),
            ("Критичная тема", _top_sla_category(snapshot)),
            (
                "Средний первый ответ",
                _format_duration(snapshot.average_first_response_time_seconds),
            ),
            ("Среднее решение", _format_duration(snapshot.average_resolution_time_seconds)),
        ]
    else:
        rows = [
            ("Открытые сейчас", str(snapshot.total_open_tickets)),
            ("Новые за период", str(snapshot.period_created_tickets_count)),
            ("Закрыто за период", str(snapshot.period_closed_tickets_count)),
            ("Средний рейтинг", _format_rating(snapshot.satisfaction_average)),
            ("Покрытие обратной связью", _format_percent(snapshot.feedback_coverage_percent)),
        ]
    return [{"label": label, "value": value} for label, value in rows]


def _top_operator_by_closures(snapshot: HelpdeskAnalyticsSnapshot) -> str:
    if not snapshot.best_operators_by_closures:
        return "нет данных"
    top = snapshot.best_operators_by_closures[0]
    return f"{top.display_name} · {top.closed_ticket_count}"


def _top_operator_by_quality(snapshot: HelpdeskAnalyticsSnapshot) -> str:
    if not snapshot.best_operators_by_satisfaction:
        return "нет данных"
    top = snapshot.best_operators_by_satisfaction[0]
    return f"{top.display_name} · {_format_rating(top.average_satisfaction)}"


def _top_category(snapshot: HelpdeskAnalyticsSnapshot) -> str:
    if not snapshot.top_categories:
        return "нет данных"
    top = snapshot.top_categories[0]
    return f"{top.category_title} · {top.created_ticket_count}"


def _best_quality_category(snapshot: HelpdeskAnalyticsSnapshot) -> str:
    categories = sorted(
        (
            item
            for item in snapshot.category_snapshots
            if item.average_satisfaction is not None and item.feedback_count > 0
        ),
        key=lambda item: (item.average_satisfaction or 0.0, item.feedback_count),
        reverse=True,
    )
    if not categories:
        return "нет данных"
    top = categories[0]
    return f"{top.category_title} · {_format_rating(top.average_satisfaction)}"


def _top_sla_category(snapshot: HelpdeskAnalyticsSnapshot) -> str:
    if not snapshot.sla_categories:
        return "нет данных"
    top = snapshot.sla_categories[0]
    return f"{top.category_title} · {top.sla_breach_count}"


def _coerce_numeric(value: object) -> float:
    if isinstance(value, bool):
        return float(int(value))
    if isinstance(value, int | float):
        return float(value)
    return 0.0


def _segment_width(value: int, total: int) -> float:
    return max(round((value / total) * 100, 2), 3)


def _bar_width(width: float, value: int) -> float:
    return max(width, 3) if value > 0 else 0


def _format_chart_value(value: float) -> str:
    if value.is_integer():
        return str(int(value))
    return f"{value:.1f}".replace(".", ",")


def _truncate(value: str, limit: int) -> str:
    if len(value) <= limit:
        return value
    return f"{value[: limit - 3].rstrip()}..."


def _format_rating(value: float | None) -> str:
    if value is None:
        return "нет данных"
    return f"{value:.1f} / 5".replace(".", ",")


def _format_percent(value: int | None) -> str:
    if value is None:
        return "нет данных"
    return f"{value}%"


def _format_duration(value: int | None) -> str:
    if value is None:
        return "нет данных"
    if value < 60:
        return f"{value} сек"
    minutes, seconds = divmod(value, 60)
    if minutes < 60:
        return f"{minutes} мин {seconds} сек"
    hours, minutes = divmod(minutes, 60)
    return f"{hours} ч {minutes} мин"


def _format_float(value: float | None) -> float:
    return 0.0 if value is None else round(value, 1)
