from __future__ import annotations

from html import escape

from application.services.stats import HelpdeskAnalyticsSnapshot, get_analytics_window_label
from application.use_cases.analytics.exports import AnalyticsSection, get_analytics_section_label


def render_analytics_snapshot_html(
    snapshot: HelpdeskAnalyticsSnapshot,
    section: AnalyticsSection,
) -> bytes:
    title = get_analytics_section_label(section)
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
      --bg: #f6f1ea;
      --panel: #fffdfa;
      --border: #ddd2c2;
      --text: #1f2430;
      --muted: #6f7782;
      --accent: #1d4d4f;
      --accent-soft: #e3efef;
      --radius: 20px;
      --shadow: 0 18px 42px rgba(31, 36, 48, 0.08);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background:
        radial-gradient(circle at top left, rgba(29, 77, 79, 0.10), transparent 32%),
        linear-gradient(180deg, #faf6f0 0%, var(--bg) 100%);
      color: var(--text);
      font-family: "IBM Plex Sans", "Segoe UI", sans-serif;
      line-height: 1.55;
      padding: 28px 16px 42px;
    }}
    .page {{ max-width: 980px; margin: 0 auto; }}
    .hero {{
      background: linear-gradient(135deg, #ffffff, #f7f2eb);
      border: 1px solid var(--border);
      border-radius: 28px;
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
    h1 {{ margin: 0 0 8px; font-size: 30px; line-height: 1.15; }}
    .hero-meta {{ color: var(--muted); }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 14px;
      margin-bottom: 18px;
    }}
    .card {{
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 18px 20px;
      box-shadow: 0 8px 24px rgba(31, 36, 48, 0.04);
    }}
    h2 {{ margin: 0 0 12px; font-size: 18px; }}
    .metric {{ display: grid; gap: 8px; }}
    .metric-row {{
      display: flex;
      justify-content: space-between;
      gap: 12px;
      border-top: 1px solid rgba(221, 210, 194, 0.65);
      padding-top: 8px;
    }}
    .metric-row:first-child {{ border-top: 0; padding-top: 0; }}
    .label {{ color: var(--muted); }}
    .value {{ font-weight: 600; text-align: right; }}
    .pill {{
      display: inline-flex;
      border-radius: 999px;
      padding: 7px 12px;
      background: var(--accent-soft);
      color: var(--accent);
      font-size: 14px;
      font-weight: 600;
      margin-top: 14px;
    }}
    @media (max-width: 640px) {{
      body {{ padding: 18px 12px 28px; }}
      .hero {{ padding: 22px 18px; }}
      h1 {{ font-size: 24px; }}
      .card {{ padding: 16px; }}
    }}
  </style>
</head>
<body>
  <div class="page">
    <section class="hero">
      <div class="eyebrow">Экспорт аналитики</div>
      <h1>{escape(title)}</h1>
      <div class="hero-meta">Период: {escape(window_label)}</div>
      <div class="pill">Снимок helpdesk</div>
    </section>
    <section class="grid">
      <article class="card">
        <h2>Сейчас</h2>
        <div class="metric">
          {_metric_row("Открытые", snapshot.total_open_tickets)}
          {_metric_row("В очереди", snapshot.queued_tickets_count)}
          {_metric_row("В работе", snapshot.assigned_tickets_count)}
          {_metric_row("Эскалация", snapshot.escalated_tickets_count)}
        </div>
      </article>
      <article class="card">
        <h2>Период</h2>
        <div class="metric">
          {_metric_row("Новые", snapshot.period_created_tickets_count)}
          {_metric_row("Закрыто", snapshot.period_closed_tickets_count)}
          {_metric_row("Оценок", snapshot.feedback_count)}
          {_metric_row("Средний рейтинг", _format_rating(snapshot.satisfaction_average))}
        </div>
      </article>
      <article class="card">
        <h2>Скорость</h2>
        <div class="metric">
          {
        _metric_row(
            "Первый ответ",
            _format_duration(snapshot.average_first_response_time_seconds),
        )
    }
          {
        _metric_row(
            "Решение",
            _format_duration(snapshot.average_resolution_time_seconds),
        )
    }
          {_metric_row("Покрытие", _format_percent(snapshot.feedback_coverage_percent))}
          {
        _metric_row(
            "SLA нарушений",
            snapshot.first_response_breach_count + snapshot.resolution_breach_count,
        )
    }
        </div>
      </article>
    </section>
    {_section_card(snapshot, section)}
  </div>
</body>
</html>
"""
    return html.encode("utf-8")


def _section_card(snapshot: HelpdeskAnalyticsSnapshot, section: AnalyticsSection) -> str:
    if section == AnalyticsSection.OPERATORS:
        rows = "".join(
            _metric_row(item.display_name, f"{item.closed_ticket_count} закрыто")
            for item in snapshot.best_operators_by_closures
        ) or _metric_row("Данные", "Недостаточно данных")
        return f'<section class="card"><h2>Операторы</h2><div class="metric">{rows}</div></section>'

    if section == AnalyticsSection.TOPICS:
        rows = "".join(
            _metric_row(item.category_title, item.created_ticket_count)
            for item in snapshot.top_categories
        ) or _metric_row("Данные", "Нет активности")
        return f'<section class="card"><h2>Темы</h2><div class="metric">{rows}</div></section>'

    if section == AnalyticsSection.QUALITY:
        rows = "".join(
            _metric_row(f"Оценка {item.rating}", item.count)
            for item in snapshot.rating_distribution
        ) or _metric_row("Данные", "Оценок пока нет")
        return f'<section class="card"><h2>Качество</h2><div class="metric">{rows}</div></section>'

    if section == AnalyticsSection.SLA:
        rows = "".join(
            _metric_row(item.category_title, item.sla_breach_count)
            for item in snapshot.sla_categories
        ) or _metric_row("Данные", "Нарушений нет")
        return f'<section class="card"><h2>SLA</h2><div class="metric">{rows}</div></section>'

    rows = "".join(
        _metric_row(item.display_name, item.ticket_count) for item in snapshot.tickets_per_operator
    ) or _metric_row("Нагрузка", "Активных назначений нет")
    return f'<section class="card"><h2>Нагрузка</h2><div class="metric">{rows}</div></section>'


def _metric_row(label: str, value: object) -> str:
    return (
        '<div class="metric-row">'
        f'<div class="label">{escape(str(label))}</div>'
        f'<div class="value">{escape(str(value))}</div>'
        "</div>"
    )


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


def _format_rating(value: float | None) -> str:
    if value is None:
        return "нет данных"
    return f"{value:.1f} / 5".replace(".", ",")


def _format_percent(value: int | None) -> str:
    if value is None:
        return "нет данных"
    return f"{value}%"
