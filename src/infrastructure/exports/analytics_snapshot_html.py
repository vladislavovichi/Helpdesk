from __future__ import annotations

from html import escape

from application.services.stats import HelpdeskAnalyticsSnapshot, get_analytics_window_label
from application.use_cases.analytics.exports import AnalyticsSection, get_analytics_section_label

SVG_WIDTH = 360
SVG_HEIGHT = 220
BAR_LEFT = 112
BAR_RIGHT = 24
BAR_MAX_WIDTH = SVG_WIDTH - BAR_LEFT - BAR_RIGHT
BAR_ROW_HEIGHT = 36


def render_analytics_snapshot_html(
    snapshot: HelpdeskAnalyticsSnapshot,
    section: AnalyticsSection,
) -> bytes:
    title = get_analytics_section_label(section)
    window_label = get_analytics_window_label(snapshot.window)
    stats_cards = "\n".join(
        (
            _stat_card(
                "Новые за период",
                snapshot.period_created_tickets_count,
                "Поток новых обращений",
            ),
            _stat_card(
                "Закрыто за период",
                snapshot.period_closed_tickets_count,
                "Результат работы команды",
            ),
            _stat_card(
                "Средний рейтинг",
                _format_rating(snapshot.satisfaction_average),
                "Клиентская оценка сервиса",
            ),
            _stat_card(
                "SLA нарушений",
                snapshot.first_response_breach_count + snapshot.resolution_breach_count,
                "Первый ответ и решение",
            ),
        )
    )
    html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Аналитика · {escape(title)}</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f6f1ea;
      --panel: rgba(255, 255, 255, 0.9);
      --panel-strong: #fffdfa;
      --border: #ddd2c2;
      --text: #1f2430;
      --muted: #6f7782;
      --accent: #1d4d4f;
      --accent-soft: #e3efef;
      --accent-2: #b76543;
      --accent-3: #8d9b6a;
      --danger: #b24f48;
      --shadow: 0 18px 42px rgba(31, 36, 48, 0.08);
      --radius-xl: 28px;
      --radius-lg: 22px;
      --radius-md: 18px;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background:
        radial-gradient(circle at top left, rgba(29, 77, 79, 0.11), transparent 32%),
        linear-gradient(180deg, #faf6f0 0%, var(--bg) 100%);
      color: var(--text);
      font-family: "IBM Plex Sans", "Segoe UI", sans-serif;
      line-height: 1.55;
      padding: 28px 16px 42px;
    }}
    .page {{ max-width: 1180px; margin: 0 auto; }}
    .hero {{
      background: linear-gradient(135deg, #ffffff, #f7f2eb);
      border: 1px solid var(--border);
      border-radius: var(--radius-xl);
      box-shadow: var(--shadow);
      padding: 28px;
      margin-bottom: 18px;
    }}
    .eyebrow {{
      color: var(--muted);
      font-size: 13px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      margin-bottom: 10px;
    }}
    h1 {{ margin: 0 0 8px; font-size: 32px; line-height: 1.12; }}
    .hero-copy {{ color: var(--muted); max-width: 760px; }}
    .hero-meta {{
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
      margin-top: 18px;
    }}
    .pill {{
      display: inline-flex;
      border-radius: 999px;
      padding: 7px 12px;
      background: var(--accent-soft);
      color: var(--accent);
      font-size: 14px;
      font-weight: 600;
    }}
    .stats-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 14px;
      margin-bottom: 18px;
    }}
    .stat-card, .section, .chart-card {{
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: var(--radius-lg);
      box-shadow: 0 10px 26px rgba(31, 36, 48, 0.05);
    }}
    .stat-card {{
      padding: 18px 20px;
    }}
    .stat-label {{
      color: var(--muted);
      font-size: 13px;
      margin-bottom: 8px;
    }}
    .stat-value {{
      font-size: 28px;
      font-weight: 700;
      line-height: 1.1;
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
      padding: 18px 18px 16px;
    }}
    .chart-card h2 {{
      margin: 0 0 6px;
      font-size: 18px;
    }}
    .chart-note {{
      color: var(--muted);
      font-size: 14px;
      margin-bottom: 10px;
    }}
    .chart-svg {{
      width: 100%;
      height: auto;
      display: block;
      overflow: visible;
    }}
    .section {{
      padding: 22px 24px;
      margin-bottom: 16px;
    }}
    .section h2 {{
      margin: 0 0 14px;
      font-size: 20px;
    }}
    .metrics {{
      display: grid;
      gap: 10px;
    }}
    .metric-row {{
      display: flex;
      justify-content: space-between;
      gap: 12px;
      padding-top: 10px;
      border-top: 1px solid rgba(221, 210, 194, 0.7);
    }}
    .metric-row:first-child {{
      border-top: 0;
      padding-top: 0;
    }}
    .label {{ color: var(--muted); }}
    .value {{ font-weight: 600; text-align: right; }}
    .legend {{
      display: grid;
      gap: 8px;
      margin-top: 10px;
    }}
    .legend-item {{
      display: flex;
      align-items: center;
      gap: 8px;
      color: var(--muted);
      font-size: 14px;
    }}
    .legend-dot {{
      width: 10px;
      height: 10px;
      border-radius: 999px;
      flex: 0 0 auto;
    }}
    @media (max-width: 640px) {{
      body {{ padding: 18px 12px 28px; }}
      .hero {{ padding: 22px 18px; }}
      h1 {{ font-size: 26px; }}
      .section {{ padding: 18px; }}
      .chart-card {{ padding: 16px; }}
    }}
  </style>
</head>
<body>
  <div class="page">
    <section class="hero">
      <div class="eyebrow">Экспорт аналитики</div>
      <h1>{escape(title)}</h1>
      <div class="hero-copy">{escape(_hero_copy(section))}</div>
      <div class="hero-meta">
        <span class="pill">Период: {escape(window_label)}</span>
        <span class="pill">HTML отчёт с графиками</span>
      </div>
    </section>
    <section class="stats-grid">
      {stats_cards}
    </section>
    <section class="charts-grid">
      {_render_status_mix_chart(snapshot)}
      {_render_category_chart(snapshot, section)}
      {_render_operator_chart(snapshot, section)}
      {_render_quality_chart(snapshot, section)}
    </section>
    <section class="section">
      <h2>Секция</h2>
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
            "Спокойный управленческий снимок по нагрузке, скорости и качеству."
        ),
        AnalyticsSection.OPERATORS: "Фокус на текущей нагрузке команды и результате операторов.",
        AnalyticsSection.TOPICS: (
            "Темы обращений, объём входящего потока и закрытия по направлениям."
        ),
        AnalyticsSection.QUALITY: "Качество сервиса, обратная связь и распределение оценок.",
        AnalyticsSection.SLA: "Контроль нарушений SLA и зон риска по категориям.",
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
        ("В очереди", snapshot.queued_tickets_count, "#b58a56"),
        ("В работе", snapshot.assigned_tickets_count, "#316a7b"),
        ("Эскалация", snapshot.escalated_tickets_count, "#b76543"),
        ("Закрытые", snapshot.closed_tickets_count, "#6d8d63"),
    )
    total = sum(value for _, value, _ in items) or 1
    x = 0.0
    segments: list[str] = []
    legend: list[str] = []
    for label, value, color in items:
        width = round((value / total) * 100, 2)
        segments.append(
            f'<rect x="{x}" y="28" width="{width}" height="24" fill="{color}" rx="8" ry="8"></rect>'
        )
        x += width
        legend.append(_legend_item(label, f"{value}", color))
    svg = (
        f'<svg class="chart-svg" viewBox="0 0 100 78" role="img" aria-label="Статусный портрет">'
        f"{''.join(segments)}"
        f'<text x="0" y="18" font-size="11" fill="#6f7782">Статусный портрет</text>'
        f'<text x="100" y="18" text-anchor="end" font-size="11" fill="#6f7782">Всего {total}</text>'
        "</svg>"
    )
    return _chart_card(
        title="Статусный портрет",
        note="Распределение текущей базы заявок по ключевым статусам.",
        chart=svg,
        legend="".join(legend),
    )


def _render_category_chart(
    snapshot: HelpdeskAnalyticsSnapshot,
    section: AnalyticsSection,
) -> str:
    if section == AnalyticsSection.SLA:
        items = [
            (item.category_title, item.sla_breach_count) for item in snapshot.sla_categories[:5]
        ]
        title = "Нарушения по темам"
        note = "Где SLA требует отдельного внимания."
        color = "#b76543"
    elif section == AnalyticsSection.TOPICS:
        items = [
            (item.category_title, item.created_ticket_count) for item in snapshot.top_categories[:5]
        ]
        title = "Поток по темам"
        note = "Самые активные причины обращений за период."
        color = "#1d4d4f"
    else:
        items = [
            (item.category_title, item.created_ticket_count) for item in snapshot.top_categories[:5]
        ]
        title = "Топ тем"
        note = "Наиболее заметные категории входящего потока."
        color = "#1d4d4f"
    return _chart_card(
        title=title,
        note=note,
        chart=_bar_chart_svg(items, color=color, value_suffix=""),
        legend="",
    )


def _render_operator_chart(
    snapshot: HelpdeskAnalyticsSnapshot,
    section: AnalyticsSection,
) -> str:
    if section == AnalyticsSection.QUALITY:
        items = [
            (item.display_name, _format_float(item.average_satisfaction))
            for item in snapshot.best_operators_by_satisfaction[:5]
        ]
        title = "Лидеры по качеству"
        note = "Операторы с лучшими оценками клиентов."
        color = "#8d9b6a"
    elif section == AnalyticsSection.OPERATORS:
        items = [
            (item.display_name, item.closed_ticket_count)
            for item in snapshot.best_operators_by_closures[:5]
        ]
        title = "Закрытия по операторам"
        note = "Кто закрыл больше дел за выбранный период."
        color = "#1d4d4f"
    else:
        items = [
            (item.display_name, item.ticket_count) for item in snapshot.tickets_per_operator[:5]
        ]
        title = "Текущая нагрузка"
        note = "Сколько активных дел у каждого оператора сейчас."
        color = "#316a7b"
    return _chart_card(
        title=title,
        note=note,
        chart=_bar_chart_svg(items, color=color, value_suffix=""),
        legend="",
    )


def _render_quality_chart(
    snapshot: HelpdeskAnalyticsSnapshot,
    section: AnalyticsSection,
) -> str:
    if section == AnalyticsSection.SLA:
        items = (
            ("Первый ответ", snapshot.first_response_breach_count),
            ("Решение", snapshot.resolution_breach_count),
        )
        title = "Срез SLA"
        note = "Сравнение типов нарушений."
        color = "#b24f48"
    else:
        items = tuple(
            (f"Оценка {item.rating}", item.count) for item in snapshot.rating_distribution
        )
        title = "Распределение оценок"
        note = "Как клиенты оценивали поддержку за выбранный период."
        color = "#b58a56"
    return _chart_card(
        title=title,
        note=note,
        chart=_bar_chart_svg(items[:5], color=color, value_suffix=""),
        legend="",
    )


def _chart_card(*, title: str, note: str, chart: str, legend: str) -> str:
    legend_html = f'<div class="legend">{legend}</div>' if legend else ""
    return (
        '<article class="chart-card">'
        f"<h2>{escape(title)}</h2>"
        f'<div class="chart-note">{escape(note)}</div>'
        f"{chart}"
        f"{legend_html}"
        "</article>"
    )


def _bar_chart_svg(
    items: list[tuple[str, object]] | tuple[tuple[str, object], ...],
    *,
    color: str,
    value_suffix: str,
) -> str:
    normalized_items = [
        (label, _coerce_numeric(value)) for label, value in items if _coerce_numeric(value) > 0
    ]
    if not normalized_items:
        return (
            f'<svg class="chart-svg" viewBox="0 0 {SVG_WIDTH} 80" '
            'role="img" aria-label="Нет данных">'
            '<text x="0" y="40" font-size="14" fill="#6f7782">'
            "Данных пока недостаточно.</text>"
            "</svg>"
        )
    max_value = max(value for _, value in normalized_items) or 1
    height = max(90, 36 + len(normalized_items) * BAR_ROW_HEIGHT)
    bars: list[str] = []
    for index, (label, value) in enumerate(normalized_items, start=0):
        y = 24 + index * BAR_ROW_HEIGHT
        width = max(8, round((value / max_value) * BAR_MAX_WIDTH, 2))
        label_html = (
            f'<text x="0" y="{y + 15}" font-size="12" fill="#6f7782">'
            f"{escape(_truncate(label, 18))}</text>"
        )
        track_html = (
            f'<rect x="{BAR_LEFT}" y="{y}" width="{BAR_MAX_WIDTH}" '
            'height="16" fill="#ede7de" rx="8"></rect>'
        )
        bar_html = (
            f'<rect x="{BAR_LEFT}" y="{y}" width="{width}" '
            f'height="16" fill="{color}" rx="8"></rect>'
        )
        value_html = (
            f'<text x="{BAR_LEFT + width + 8}" y="{y + 13}" '
            'font-size="12" fill="#1f2430">'
            f"{escape(_format_chart_value(value, value_suffix))}</text>"
        )
        bars.append(
            f"{label_html}{track_html}{bar_html}{value_html}"
        )
    return (
        f'<svg class="chart-svg" viewBox="0 0 {SVG_WIDTH} {height}" role="img" aria-label="График">'
        f"{''.join(bars)}"
        "</svg>"
    )


def _render_section_metrics(snapshot: HelpdeskAnalyticsSnapshot, section: AnalyticsSection) -> str:
    if section == AnalyticsSection.OPERATORS:
        rows = [
            _metric_row(
                "Активных назначений",
                sum(item.ticket_count for item in snapshot.tickets_per_operator),
            ),
            _metric_row("Лучший по закрытиям", _top_operator_by_closures(snapshot)),
            _metric_row("Лучший по качеству", _top_operator_by_quality(snapshot)),
            _metric_row(
                "Средний первый ответ",
                _format_duration(snapshot.average_first_response_time_seconds),
            ),
            _metric_row(
                "Среднее решение", _format_duration(snapshot.average_resolution_time_seconds)
            ),
        ]
    elif section == AnalyticsSection.TOPICS:
        rows = [
            _metric_row("Самая активная тема", _top_category(snapshot)),
            _metric_row(
                "Открытых по темам",
                sum(item.open_ticket_count for item in snapshot.category_snapshots),
            ),
            _metric_row(
                "Закрыто по темам",
                sum(item.closed_ticket_count for item in snapshot.category_snapshots),
            ),
            _metric_row("Лучшая тема по качеству", _best_quality_category(snapshot)),
        ]
    elif section == AnalyticsSection.QUALITY:
        rows = [
            _metric_row("Средний рейтинг", _format_rating(snapshot.satisfaction_average)),
            _metric_row("Оценок", snapshot.feedback_count),
            _metric_row("Покрытие", _format_percent(snapshot.feedback_coverage_percent)),
            _metric_row("Лучший оператор", _top_operator_by_quality(snapshot)),
            _metric_row("Лучшая тема", _best_quality_category(snapshot)),
        ]
    elif section == AnalyticsSection.SLA:
        rows = [
            _metric_row("Нарушения первого ответа", snapshot.first_response_breach_count),
            _metric_row("Нарушения решения", snapshot.resolution_breach_count),
            _metric_row("Критичная тема", _top_sla_category(snapshot)),
            _metric_row(
                "Средний первый ответ",
                _format_duration(snapshot.average_first_response_time_seconds),
            ),
            _metric_row(
                "Среднее решение", _format_duration(snapshot.average_resolution_time_seconds)
            ),
        ]
    else:
        rows = [
            _metric_row("Открытые сейчас", snapshot.total_open_tickets),
            _metric_row("Новые за период", snapshot.period_created_tickets_count),
            _metric_row("Закрыто за период", snapshot.period_closed_tickets_count),
            _metric_row("Средний рейтинг", _format_rating(snapshot.satisfaction_average)),
            _metric_row(
                "Покрытие обратной связью", _format_percent(snapshot.feedback_coverage_percent)
            ),
        ]
    return f'<div class="metrics">{"".join(rows)}</div>'


def _metric_row(label: str, value: object) -> str:
    return (
        '<div class="metric-row">'
        f'<div class="label">{escape(str(label))}</div>'
        f'<div class="value">{escape(str(value))}</div>'
        "</div>"
    )


def _legend_item(label: str, value: str, color: str) -> str:
    return (
        '<div class="legend-item">'
        f'<span class="legend-dot" style="background:{color}"></span>'
        f"<span>{escape(label)} · {escape(value)}</span>"
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


def _format_chart_value(value: float, suffix: str) -> str:
    if value.is_integer():
        return f"{int(value)}{suffix}"
    return f"{value:.1f}{suffix}".replace(".", ",")


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
