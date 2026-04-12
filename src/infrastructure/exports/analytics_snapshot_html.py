from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from html import escape

from application.services.stats import HelpdeskAnalyticsSnapshot, get_analytics_window_label
from application.use_cases.analytics.exports import AnalyticsSection, get_analytics_section_label


def render_analytics_snapshot_html(
    snapshot: HelpdeskAnalyticsSnapshot,
    section: AnalyticsSection,
) -> bytes:
    title = get_analytics_section_label(section)
    generated_at = datetime.now(UTC).strftime("%d.%m.%Y %H:%M UTC")
    window_label = get_analytics_window_label(snapshot.window)
    html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Аналитика · {escape(title)}</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f4efe8;
      --paper: rgba(255, 252, 247, 0.94);
      --paper-strong: #fffdf9;
      --line: rgba(79, 66, 52, 0.12);
      --line-strong: rgba(79, 66, 52, 0.18);
      --text: #20242a;
      --muted: #6d727b;
      --accent: #275764;
      --accent-2: #8e6646;
      --accent-3: #6e8460;
      --danger: #a04d48;
      --shadow: 0 22px 60px rgba(32, 36, 42, 0.08);
      --radius-xl: 32px;
      --radius-lg: 24px;
      --radius-md: 18px;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background:
        radial-gradient(circle at top left, rgba(39, 87, 100, 0.10), transparent 30%),
        linear-gradient(180deg, #faf7f1 0%, var(--bg) 100%);
      color: var(--text);
      font-family: "SF Pro Text", "Segoe UI", sans-serif;
      line-height: 1.58;
      padding: 28px 16px 44px;
    }}
    .page {{ max-width: 1180px; margin: 0 auto; }}
    .hero {{
      background: linear-gradient(160deg, rgba(255, 255, 255, 0.96), rgba(247, 242, 234, 0.98));
      border: 1px solid var(--line);
      border-radius: var(--radius-xl);
      box-shadow: var(--shadow);
      padding: 30px;
      margin-bottom: 18px;
    }}
    .eyebrow {{
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.12em;
      margin-bottom: 12px;
    }}
    h1, h2 {{
      font-family: "Iowan Old Style", "Palatino Linotype", Georgia, serif;
      font-weight: 600;
      letter-spacing: -0.02em;
    }}
    h1 {{
      margin: 0 0 10px;
      font-size: 38px;
      line-height: 1.06;
    }}
    .hero-copy {{
      max-width: 760px;
      color: rgba(32, 36, 42, 0.86);
      font-size: 18px;
    }}
    .pill-row {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-top: 18px;
    }}
    .pill {{
      display: inline-flex;
      align-items: center;
      padding: 8px 14px;
      border-radius: 999px;
      background: rgba(39, 87, 100, 0.10);
      color: var(--accent);
      font-size: 14px;
      font-weight: 600;
    }}
    .stats-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 12px;
      margin-bottom: 18px;
    }}
    .stat-card, .chart-card, .section {{
      background: var(--paper);
      border: 1px solid var(--line);
      border-radius: var(--radius-lg);
      box-shadow: 0 10px 26px rgba(32, 36, 42, 0.05);
    }}
    .stat-card {{
      padding: 18px;
    }}
    .stat-label {{
      color: var(--muted);
      font-size: 13px;
      margin-bottom: 8px;
    }}
    .stat-value {{
      font-size: 28px;
      font-weight: 700;
      line-height: 1.08;
      margin-bottom: 6px;
    }}
    .stat-note {{
      color: var(--muted);
      font-size: 14px;
    }}
    .charts-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
      gap: 14px;
      margin-bottom: 18px;
    }}
    .chart-card {{
      padding: 18px 18px 14px;
    }}
    .chart-card h2 {{
      margin: 0 0 6px;
      font-size: 22px;
    }}
    .chart-note {{
      color: var(--muted);
      font-size: 14px;
      margin-bottom: 12px;
    }}
    .chart-body {{
      display: grid;
      gap: 12px;
    }}
    .segment-track {{
      display: flex;
      min-height: 18px;
      background: #ece4d9;
      border-radius: 999px;
      overflow: hidden;
    }}
    .segment-fill {{
      min-width: 10px;
    }}
    .segment-legend {{
      display: grid;
      gap: 8px;
    }}
    .legend-row {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 14px;
      align-items: start;
      font-size: 14px;
    }}
    .legend-label {{
      color: var(--text);
      word-break: break-word;
    }}
    .legend-value {{
      color: var(--muted);
      white-space: nowrap;
      text-align: right;
    }}
    .bar-chart {{
      display: grid;
      gap: 12px;
    }}
    .bar-row {{
      display: grid;
      gap: 6px;
    }}
    .bar-head {{
      display: flex;
      justify-content: space-between;
      gap: 14px;
      align-items: baseline;
    }}
    .bar-label {{
      font-size: 14px;
      word-break: break-word;
    }}
    .bar-value {{
      color: var(--muted);
      font-size: 13px;
      white-space: nowrap;
    }}
    .bar-track {{
      height: 12px;
      border-radius: 999px;
      overflow: hidden;
      background: #ece4d9;
    }}
    .bar-fill {{
      height: 100%;
      border-radius: 999px;
    }}
    .section {{
      padding: 24px;
    }}
    .section h2 {{
      margin: 0 0 14px;
      font-size: 24px;
    }}
    .metrics {{
      display: grid;
      gap: 10px;
    }}
    .metric-row {{
      display: flex;
      justify-content: space-between;
      align-items: baseline;
      gap: 16px;
      padding-top: 10px;
      border-top: 1px solid var(--line);
    }}
    .metric-row:first-child {{
      border-top: 0;
      padding-top: 0;
    }}
    .metric-label {{
      color: var(--muted);
    }}
    .metric-value {{
      font-weight: 700;
      text-align: right;
    }}
    @media (max-width: 680px) {{
      body {{ padding: 18px 12px 30px; }}
      .hero {{ padding: 24px 22px; }}
      h1 {{ font-size: 30px; }}
      .section {{ padding: 20px; }}
      .legend-row {{
        grid-template-columns: 1fr;
        gap: 2px;
      }}
      .legend-value {{
        text-align: left;
      }}
      .bar-head {{
        flex-direction: column;
        align-items: flex-start;
        gap: 4px;
      }}
    }}
  </style>
</head>
<body>
  <div class="page">
    <section class="hero">
      <div class="eyebrow">HTML отчёт с графиками</div>
      <h1>{escape(title)}</h1>
      <div class="hero-copy">{escape(_hero_copy(section))}</div>
      <div class="pill-row">
        <span class="pill">Период: {escape(window_label)}</span>
        <span class="pill">Подготовлен: {escape(generated_at)}</span>
        <span class="pill">Executive view</span>
      </div>
    </section>
    <section class="stats-grid">
      {_stat_card("Новые за период", snapshot.period_created_tickets_count, "Входящий поток")}
      {_stat_card("Закрыто за период", snapshot.period_closed_tickets_count, "Завершённые дела")}
      {
        _stat_card(
            "Средний рейтинг",
            _format_rating(snapshot.satisfaction_average),
            "Клиентская оценка",
        )
    }
      {
        _stat_card(
            "Нарушения SLA",
            str(snapshot.first_response_breach_count + snapshot.resolution_breach_count),
            "Первый ответ и решение",
        )
    }
    </section>
    <section class="charts-grid">
      {_render_status_mix_chart(snapshot)}
      {_render_volume_chart(snapshot)}
      {_render_category_chart(snapshot, section)}
      {_render_quality_chart(snapshot, section)}
      {_render_operator_chart(snapshot, section)}
    </section>
    <section class="section">
      <h2>Ключевые показатели</h2>
      {_render_section_metrics(snapshot, section)}
    </section>
  </div>
</body>
</html>
"""
    return html.encode("utf-8")


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


def _stat_card(label: str, value: object, note: str) -> str:
    return (
        '<article class="stat-card">'
        f'<div class="stat-label">{escape(str(label))}</div>'
        f'<div class="stat-value">{escape(str(value))}</div>'
        f'<div class="stat-note">{escape(note)}</div>'
        "</article>"
    )


def _render_status_mix_chart(snapshot: HelpdeskAnalyticsSnapshot) -> str:
    items = (
        ("В очереди", snapshot.queued_tickets_count, "#9c7a57"),
        ("В работе", snapshot.assigned_tickets_count, "#275764"),
        ("Эскалация", snapshot.escalated_tickets_count, "#a04d48"),
        ("Закрытые", snapshot.closed_tickets_count, "#6e8460"),
    )
    total = sum(value for _, value, _ in items) or 1
    track = "".join(
        (
            f'<div class="segment-fill" style="width: {max(round((value / total) * 100, 2), 3)}%; '
            f'background: {color};"></div>'
        )
        for _, value, color in items
        if value > 0
    )
    legend = "".join(
        (
            '<div class="legend-row">'
            f'<div class="legend-label">{escape(label)}</div>'
            f'<div class="legend-value">'
            f"{value} · {_format_percent(round((value / total) * 100))}"
            "</div>"
            "</div>"
        )
        for label, value, _ in items
    )
    chart = (
        '<div class="chart-body">'
        f'<div class="legend-value">Всего {total}</div>'
        f'<div class="segment-track" role="img" aria-label="Статусный портрет">{track}</div>'
        f'<div class="segment-legend">{legend}</div>'
        "</div>"
    )
    return _chart_card(
        title="Статусный портрет",
        note="Распределение текущей базы заявок по ключевым статусам.",
        chart=chart,
    )


def _render_volume_chart(snapshot: HelpdeskAnalyticsSnapshot) -> str:
    chart = _render_dual_bar_chart(
        items=(
            ("Создано", snapshot.period_created_tickets_count, "#275764"),
            ("Закрыто", snapshot.period_closed_tickets_count, "#6e8460"),
        )
    )
    return _chart_card(
        title="Объём периода",
        note="Сравнение входящего потока и закрытых дел за выбранное окно.",
        chart=chart,
    )


def _render_category_chart(
    snapshot: HelpdeskAnalyticsSnapshot,
    section: AnalyticsSection,
) -> str:
    items: Sequence[tuple[str | None, int | float]]
    if section == AnalyticsSection.SLA:
        items = [
            (item.category_title, item.sla_breach_count) for item in snapshot.sla_categories[:5]
        ]
        title = "Нарушения по темам"
        note = "Где SLA проседает сильнее всего."
        color = "#a04d48"
    else:
        items = [
            (item.category_title, item.created_ticket_count) for item in snapshot.top_categories[:5]
        ]
        title = "Топ тем"
        note = "Самые заметные направления входящего потока."
        color = "#275764"
    return _chart_card(
        title=title,
        note=note,
        chart=_bar_chart_html(items, color=color),
    )


def _render_quality_chart(
    snapshot: HelpdeskAnalyticsSnapshot,
    section: AnalyticsSection,
) -> str:
    items: Sequence[tuple[str | None, int | float]]
    if section == AnalyticsSection.SLA:
        items = [
            ("Первый ответ", snapshot.first_response_breach_count),
            ("Решение", snapshot.resolution_breach_count),
        ]
        title = "Срез SLA"
        note = "Разделение нарушений по типу."
        color = "#a04d48"
    else:
        items = tuple(
            (f"Оценка {item.rating}", item.count) for item in snapshot.rating_distribution
        )
        title = "Распределение оценок"
        note = "Как клиенты оценивали поддержку."
        color = "#8e6646"
    return _chart_card(
        title=title,
        note=note,
        chart=_bar_chart_html(items[:5], color=color),
    )


def _render_operator_chart(
    snapshot: HelpdeskAnalyticsSnapshot,
    section: AnalyticsSection,
) -> str:
    items: Sequence[tuple[str | None, int | float]]
    if section == AnalyticsSection.OPERATORS:
        items = [
            (item.display_name, item.closed_ticket_count)
            for item in snapshot.best_operators_by_closures[:5]
        ]
        title = "Закрытия по операторам"
        note = "Кто дал основной результат за период."
        color = "#275764"
    elif section == AnalyticsSection.QUALITY:
        items = [
            (item.display_name, _format_float(item.average_satisfaction))
            for item in snapshot.best_operators_by_satisfaction[:5]
        ]
        title = "Лидеры по качеству"
        note = "Операторы с лучшей клиентской оценкой."
        color = "#6e8460"
    else:
        items = [
            (item.display_name, item.ticket_count) for item in snapshot.tickets_per_operator[:5]
        ]
        title = "Текущая нагрузка"
        note = "Сколько активных дел сейчас у каждого оператора."
        color = "#275764"
    return _chart_card(
        title=title,
        note=note,
        chart=_bar_chart_html(items, color=color),
    )


def _chart_card(*, title: str, note: str, chart: str) -> str:
    return (
        '<article class="chart-card">'
        f"<h2>{escape(title)}</h2>"
        f'<div class="chart-note">{escape(note)}</div>'
        f"{chart}"
        "</article>"
    )


def _render_dual_bar_chart(
    items: Sequence[tuple[str, int, str]],
) -> str:
    max_value = max((value for _, value, _ in items), default=1) or 1
    rows = []
    for label, value, color in items:
        width = round((value / max_value) * 100, 2)
        rows.append(
            '<div class="bar-row">'
            f'<div class="bar-head"><div class="bar-label">{escape(label)}</div>'
            f'<div class="bar-value">{value}</div></div>'
            '<div class="bar-track">'
            f'<div class="bar-fill" style="width: {max(width, 3)}%; background: {color};"></div>'
            "</div>"
            "</div>"
        )
    return f'<div class="bar-chart">{"".join(rows)}</div>'


def _bar_chart_html(
    items: Sequence[tuple[str | None, int | float]],
    *,
    color: str,
) -> str:
    normalized_items = [
        ((label or "Без названия"), _coerce_numeric(value))
        for label, value in items
        if _coerce_numeric(value) > 0
    ]
    if not normalized_items:
        return '<div class="chart-note">Данных пока недостаточно.</div>'
    max_value = max(value for _, value in normalized_items) or 1
    rows: list[str] = []
    for label, value in normalized_items:
        width = round((value / max_value) * 100, 2)
        rows.append(
            '<div class="bar-row">'
            f'<div class="bar-head"><div class="bar-label">{escape(_truncate(label, 44))}</div>'
            f'<div class="bar-value">{escape(_format_chart_value(value))}</div></div>'
            '<div class="bar-track">'
            f'<div class="bar-fill" style="width: {max(width, 3)}%; background: {color};"></div>'
            "</div>"
            "</div>"
        )
    return f'<div class="bar-chart">{"".join(rows)}</div>'


def _render_section_metrics(snapshot: HelpdeskAnalyticsSnapshot, section: AnalyticsSection) -> str:
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
    return (
        '<div class="metrics">'
        + "".join(_metric_row(label, value) for label, value in rows)
        + "</div>"
    )


def _metric_row(label: str, value: object) -> str:
    return (
        '<div class="metric-row">'
        f'<div class="metric-label">{escape(label)}</div>'
        f'<div class="metric-value">{escape(str(value))}</div>'
        "</div>"
    )


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
