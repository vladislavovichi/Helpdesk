from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum

from application.services.stats import (
    AnalyticsWindow,
    HelpdeskAnalyticsSnapshot,
    HelpdeskStatsService,
)


class AnalyticsSection(StrEnum):
    OVERVIEW = "overview"
    OPERATORS = "operators"
    TOPICS = "topics"
    QUALITY = "quality"
    SLA = "sla"


class AnalyticsExportFormat(StrEnum):
    CSV = "csv"
    HTML = "html"


@dataclass(slots=True, frozen=True)
class AnalyticsSnapshotExport:
    format: AnalyticsExportFormat
    filename: str
    content_type: str
    content: bytes
    section: AnalyticsSection
    window: AnalyticsWindow


AnalyticsSnapshotRenderer = Callable[[HelpdeskAnalyticsSnapshot, AnalyticsSection], bytes]


class ExportAnalyticsSnapshotUseCase:
    def __init__(
        self,
        *,
        stats_service: HelpdeskStatsService,
        csv_renderer: AnalyticsSnapshotRenderer,
        html_renderer: AnalyticsSnapshotRenderer,
    ) -> None:
        self.stats_service = stats_service
        self.csv_renderer = csv_renderer
        self.html_renderer = html_renderer

    async def __call__(
        self,
        *,
        window: AnalyticsWindow,
        section: AnalyticsSection,
        format: AnalyticsExportFormat,
    ) -> AnalyticsSnapshotExport:
        snapshot = await self.stats_service.get_analytics_snapshot(window=window)
        if format == AnalyticsExportFormat.CSV:
            return AnalyticsSnapshotExport(
                format=format,
                filename=_build_filename(section=section, window=window, extension="csv"),
                content_type="text/csv",
                content=self.csv_renderer(snapshot, section),
                section=section,
                window=window,
            )

        return AnalyticsSnapshotExport(
            format=format,
            filename=_build_filename(section=section, window=window, extension="html"),
            content_type="text/html",
            content=self.html_renderer(snapshot, section),
            section=section,
            window=window,
        )


def get_analytics_section_label(section: AnalyticsSection) -> str:
    labels = {
        AnalyticsSection.OVERVIEW: "Общая",
        AnalyticsSection.OPERATORS: "Операторы",
        AnalyticsSection.TOPICS: "Темы",
        AnalyticsSection.QUALITY: "Качество",
        AnalyticsSection.SLA: "SLA",
    }
    return labels[section]


def _build_filename(
    *,
    section: AnalyticsSection,
    window: AnalyticsWindow,
    extension: str,
) -> str:
    return f"analytics-{section.value}-{window.value}.{extension}"
