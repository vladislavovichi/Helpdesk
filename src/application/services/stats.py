from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any

from domain.contracts.repositories import (
    CategoryFeedbackStatsRecord,
    CategoryTicketCountRecord,
    OperatorClosureStatsRecord,
    SLABreachCountRecord,
    TicketAnalyticsRepository,
)
from domain.enums.tickets import TicketStatus


class AnalyticsWindow(StrEnum):
    TODAY = "today"
    DAYS_7 = "7d"
    DAYS_30 = "30d"
    ALL = "all"


@dataclass(slots=True, frozen=True)
class OperatorTicketLoad:
    operator_id: int
    display_name: str
    ticket_count: int


@dataclass(slots=True, frozen=True)
class AnalyticsRatingBucket:
    rating: int
    count: int


@dataclass(slots=True, frozen=True)
class AnalyticsOperatorSnapshot:
    operator_id: int
    display_name: str
    active_ticket_count: int
    closed_ticket_count: int
    average_first_response_time_seconds: int | None
    average_resolution_time_seconds: int | None
    average_satisfaction: float | None
    feedback_count: int


@dataclass(slots=True, frozen=True)
class AnalyticsCategorySnapshot:
    category_id: int | None
    category_title: str
    created_ticket_count: int
    open_ticket_count: int
    closed_ticket_count: int
    average_satisfaction: float | None
    feedback_count: int
    sla_breach_count: int


@dataclass(slots=True, frozen=True)
class HelpdeskOperationalStats:
    total_open_tickets: int
    queued_tickets_count: int
    assigned_tickets_count: int
    escalated_tickets_count: int
    closed_tickets_count: int
    tickets_per_operator: tuple[OperatorTicketLoad, ...]
    average_first_response_time_seconds: int | None
    average_resolution_time_seconds: int | None


@dataclass(slots=True, frozen=True)
class HelpdeskAnalyticsSnapshot:
    window: AnalyticsWindow
    total_open_tickets: int
    queued_tickets_count: int
    assigned_tickets_count: int
    escalated_tickets_count: int
    closed_tickets_count: int
    tickets_per_operator: tuple[OperatorTicketLoad, ...]
    period_created_tickets_count: int
    period_closed_tickets_count: int
    average_first_response_time_seconds: int | None
    average_resolution_time_seconds: int | None
    satisfaction_average: float | None
    feedback_count: int
    feedback_coverage_percent: int | None
    rating_distribution: tuple[AnalyticsRatingBucket, ...]
    operator_snapshots: tuple[AnalyticsOperatorSnapshot, ...]
    category_snapshots: tuple[AnalyticsCategorySnapshot, ...]
    best_operators_by_closures: tuple[AnalyticsOperatorSnapshot, ...]
    best_operators_by_satisfaction: tuple[AnalyticsOperatorSnapshot, ...]
    top_categories: tuple[AnalyticsCategorySnapshot, ...]
    first_response_breach_count: int
    resolution_breach_count: int
    sla_categories: tuple[AnalyticsCategorySnapshot, ...]


@dataclass(slots=True, frozen=True)
class _AnalyticsSnapshotQueries:
    operational: HelpdeskOperationalStats
    period_created_tickets_count: int
    period_closed_tickets_count: int
    average_first_response_seconds: float | None
    average_resolution_seconds: float | None
    satisfaction_average: float | None
    feedback_count: int
    rating_distribution: Sequence[Any]
    operator_stats: Sequence[OperatorClosureStatsRecord]
    created_by_category: Sequence[CategoryTicketCountRecord]
    open_by_category: Sequence[CategoryTicketCountRecord]
    closed_by_category: Sequence[CategoryTicketCountRecord]
    feedback_by_category: Sequence[CategoryFeedbackStatsRecord]
    sla_breaches: Mapping[str, int]
    sla_by_category: Sequence[SLABreachCountRecord]


@dataclass(slots=True, frozen=True)
class _AnalyticsSnapshotAggregates:
    tickets_per_operator: tuple[OperatorTicketLoad, ...]
    operator_snapshots: tuple[AnalyticsOperatorSnapshot, ...]
    category_snapshots: tuple[AnalyticsCategorySnapshot, ...]
    best_operators_by_closures: tuple[AnalyticsOperatorSnapshot, ...]
    best_operators_by_satisfaction: tuple[AnalyticsOperatorSnapshot, ...]
    top_categories: tuple[AnalyticsCategorySnapshot, ...]
    sla_categories: tuple[AnalyticsCategorySnapshot, ...]
    feedback_coverage_percent: int | None


def utcnow() -> datetime:
    return datetime.now(UTC)


def get_analytics_window_label(window: AnalyticsWindow) -> str:
    labels = {
        AnalyticsWindow.TODAY: "сегодня",
        AnalyticsWindow.DAYS_7: "7 дней",
        AnalyticsWindow.DAYS_30: "30 дней",
        AnalyticsWindow.ALL: "всё время",
    }
    return labels[window]


def _normalize_average_seconds(value: float | None) -> int | None:
    if value is None:
        return None
    if value < 0:
        return 0
    return int(round(value))


def _normalize_average_rating(value: float | None) -> float | None:
    if value is None:
        return None
    if value < 0:
        return 0.0
    return round(value, 1)


def _resolve_window_start(window: AnalyticsWindow, *, now: datetime) -> datetime | None:
    if window == AnalyticsWindow.ALL:
        return None
    if window == AnalyticsWindow.TODAY:
        return now.replace(hour=0, minute=0, second=0, microsecond=0)
    if window == AnalyticsWindow.DAYS_7:
        return now - timedelta(days=7)
    return now - timedelta(days=30)


class HelpdeskStatsService:
    """Aggregate pragmatic operational metrics and richer analytics snapshots."""

    def __init__(
        self,
        analytics_repository: TicketAnalyticsRepository,
        *,
        now_provider: Callable[[], datetime] = utcnow,
    ) -> None:
        self.analytics_repository = analytics_repository
        self.now_provider = now_provider

    async def get_operational_stats(self) -> HelpdeskOperationalStats:
        by_status = dict(await self.analytics_repository.count_by_status())
        tickets_per_operator = await self.analytics_repository.count_active_tickets_per_operator()
        average_first_response_seconds = (
            await self.analytics_repository.get_average_first_response_time_seconds()
        )
        average_resolution_seconds = (
            await self.analytics_repository.get_average_resolution_time_seconds()
        )

        return HelpdeskOperationalStats(
            total_open_tickets=sum(
                count for status, count in by_status.items() if status != TicketStatus.CLOSED
            ),
            queued_tickets_count=by_status.get(TicketStatus.QUEUED, 0),
            assigned_tickets_count=by_status.get(TicketStatus.ASSIGNED, 0),
            escalated_tickets_count=by_status.get(TicketStatus.ESCALATED, 0),
            closed_tickets_count=by_status.get(TicketStatus.CLOSED, 0),
            tickets_per_operator=tuple(
                OperatorTicketLoad(
                    operator_id=item.operator_id,
                    display_name=item.display_name,
                    ticket_count=item.ticket_count,
                )
                for item in tickets_per_operator
            ),
            average_first_response_time_seconds=_normalize_average_seconds(
                average_first_response_seconds
            ),
            average_resolution_time_seconds=_normalize_average_seconds(average_resolution_seconds),
        )

    async def get_analytics_snapshot(
        self,
        *,
        window: AnalyticsWindow,
    ) -> HelpdeskAnalyticsSnapshot:
        since = _resolve_window_start(window, now=self.now_provider())
        queries = await self._query_analytics_snapshot(since=since)
        aggregates = self._aggregate_analytics_snapshot(queries)
        return self._assemble_analytics_snapshot(
            window=window,
            queries=queries,
            aggregates=aggregates,
        )

    async def _query_analytics_snapshot(
        self,
        *,
        since: datetime | None,
    ) -> _AnalyticsSnapshotQueries:
        operational = await self.get_operational_stats()
        return _AnalyticsSnapshotQueries(
            operational=operational,
            period_created_tickets_count=(
                await self.analytics_repository.count_created_tickets(since=since)
            ),
            period_closed_tickets_count=(
                await self.analytics_repository.count_closed_tickets(since=since)
            ),
            average_first_response_seconds=(
                await self.analytics_repository.get_average_first_response_time_seconds(since=since)
            ),
            average_resolution_seconds=(
                await self.analytics_repository.get_average_resolution_time_seconds(since=since)
            ),
            satisfaction_average=(
                await self.analytics_repository.get_average_feedback_rating(since=since)
            ),
            feedback_count=(
                await self.analytics_repository.count_feedback_submissions(since=since)
            ),
            rating_distribution=(
                await self.analytics_repository.get_feedback_rating_distribution(since=since)
            ),
            operator_stats=(
                await self.analytics_repository.list_closed_ticket_stats_by_operator(since=since)
            ),
            created_by_category=(
                await self.analytics_repository.list_created_ticket_counts_by_category(since=since)
            ),
            open_by_category=(
                await self.analytics_repository.list_open_ticket_counts_by_category()
            ),
            closed_by_category=(
                await self.analytics_repository.list_closed_ticket_counts_by_category(since=since)
            ),
            feedback_by_category=(
                await self.analytics_repository.list_feedback_stats_by_category(since=since)
            ),
            sla_breaches=await self.analytics_repository.count_sla_breaches(since=since),
            sla_by_category=(
                await self.analytics_repository.list_sla_breach_counts_by_category(since=since)
            ),
        )

    def _aggregate_analytics_snapshot(
        self,
        queries: _AnalyticsSnapshotQueries,
    ) -> _AnalyticsSnapshotAggregates:
        tickets_per_operator = queries.operational.tickets_per_operator
        operator_snapshots = _merge_operator_snapshots(
            active_loads=tickets_per_operator,
            operator_stats=queries.operator_stats,
        )
        category_snapshots = _merge_category_snapshots(
            created_counts=queries.created_by_category,
            open_counts=queries.open_by_category,
            closed_counts=queries.closed_by_category,
            feedback_stats=queries.feedback_by_category,
            sla_counts=queries.sla_by_category,
        )

        best_operators_by_closures = tuple(
            sorted(
                operator_snapshots,
                key=lambda item: (
                    item.closed_ticket_count,
                    item.feedback_count,
                    item.display_name.lower(),
                ),
                reverse=True,
            )[:5]
        )
        best_operators_by_satisfaction = tuple(
            sorted(
                (
                    item
                    for item in operator_snapshots
                    if item.average_satisfaction is not None and item.feedback_count > 0
                ),
                key=lambda item: (
                    item.average_satisfaction or 0.0,
                    item.feedback_count,
                    item.closed_ticket_count,
                    item.display_name.lower(),
                ),
                reverse=True,
            )[:5]
        )
        top_categories = tuple(
            sorted(
                category_snapshots,
                key=lambda item: (
                    item.created_ticket_count,
                    item.closed_ticket_count,
                    item.category_title.lower(),
                ),
                reverse=True,
            )[:5]
        )
        sla_categories = tuple(
            sorted(
                (item for item in category_snapshots if item.sla_breach_count > 0),
                key=lambda item: (item.sla_breach_count, item.category_title.lower()),
                reverse=True,
            )[:5]
        )

        feedback_coverage_percent: int | None = None
        if queries.period_closed_tickets_count > 0:
            feedback_coverage_percent = int(
                round((queries.feedback_count / queries.period_closed_tickets_count) * 100)
            )

        return _AnalyticsSnapshotAggregates(
            tickets_per_operator=tickets_per_operator,
            operator_snapshots=operator_snapshots,
            category_snapshots=category_snapshots,
            best_operators_by_closures=best_operators_by_closures,
            best_operators_by_satisfaction=best_operators_by_satisfaction,
            top_categories=top_categories,
            sla_categories=sla_categories,
            feedback_coverage_percent=feedback_coverage_percent,
        )

    def _assemble_analytics_snapshot(
        self,
        *,
        window: AnalyticsWindow,
        queries: _AnalyticsSnapshotQueries,
        aggregates: _AnalyticsSnapshotAggregates,
    ) -> HelpdeskAnalyticsSnapshot:
        operational = queries.operational
        return HelpdeskAnalyticsSnapshot(
            window=window,
            total_open_tickets=operational.total_open_tickets,
            queued_tickets_count=operational.queued_tickets_count,
            assigned_tickets_count=operational.assigned_tickets_count,
            escalated_tickets_count=operational.escalated_tickets_count,
            closed_tickets_count=operational.closed_tickets_count,
            tickets_per_operator=aggregates.tickets_per_operator,
            period_created_tickets_count=queries.period_created_tickets_count,
            period_closed_tickets_count=queries.period_closed_tickets_count,
            average_first_response_time_seconds=_normalize_average_seconds(
                queries.average_first_response_seconds
            ),
            average_resolution_time_seconds=_normalize_average_seconds(
                queries.average_resolution_seconds
            ),
            satisfaction_average=_normalize_average_rating(queries.satisfaction_average),
            feedback_count=queries.feedback_count,
            feedback_coverage_percent=aggregates.feedback_coverage_percent,
            rating_distribution=tuple(
                AnalyticsRatingBucket(rating=item.rating, count=item.count)
                for item in queries.rating_distribution
            ),
            operator_snapshots=aggregates.operator_snapshots,
            category_snapshots=aggregates.category_snapshots,
            best_operators_by_closures=aggregates.best_operators_by_closures,
            best_operators_by_satisfaction=aggregates.best_operators_by_satisfaction,
            top_categories=aggregates.top_categories,
            first_response_breach_count=queries.sla_breaches.get(
                "sla_breached_first_response",
                0,
            ),
            resolution_breach_count=queries.sla_breaches.get("sla_breached_resolution", 0),
            sla_categories=aggregates.sla_categories,
        )


def _merge_operator_snapshots(
    *,
    active_loads: tuple[OperatorTicketLoad, ...],
    operator_stats: Sequence[OperatorClosureStatsRecord],
) -> tuple[AnalyticsOperatorSnapshot, ...]:
    load_map = {item.operator_id: item for item in active_loads}
    stats_map = {item.operator_id: item for item in operator_stats}
    operator_ids = set(load_map) | set(stats_map)

    snapshots = []
    for operator_id in operator_ids:
        load = load_map.get(operator_id)
        stats = stats_map.get(operator_id)
        display_name = (
            load.display_name
            if load is not None
            else (stats.display_name if stats is not None else f"Оператор {operator_id}")
        )
        snapshots.append(
            AnalyticsOperatorSnapshot(
                operator_id=operator_id,
                display_name=display_name,
                active_ticket_count=0 if load is None else load.ticket_count,
                closed_ticket_count=0 if stats is None else stats.closed_ticket_count,
                average_first_response_time_seconds=(
                    None
                    if stats is None
                    else _normalize_average_seconds(stats.average_first_response_time_seconds)
                ),
                average_resolution_time_seconds=(
                    None
                    if stats is None
                    else _normalize_average_seconds(stats.average_resolution_time_seconds)
                ),
                average_satisfaction=(
                    None if stats is None else _normalize_average_rating(stats.average_satisfaction)
                ),
                feedback_count=0 if stats is None else stats.feedback_count,
            )
        )

    return tuple(
        sorted(
            snapshots,
            key=lambda item: (
                item.active_ticket_count,
                item.closed_ticket_count,
                item.display_name.lower(),
            ),
            reverse=True,
        )
    )


def _merge_category_snapshots(
    *,
    created_counts: Sequence[CategoryTicketCountRecord],
    open_counts: Sequence[CategoryTicketCountRecord],
    closed_counts: Sequence[CategoryTicketCountRecord],
    feedback_stats: Sequence[CategoryFeedbackStatsRecord],
    sla_counts: Sequence[SLABreachCountRecord],
) -> tuple[AnalyticsCategorySnapshot, ...]:
    created_map = {
        _category_key(item.category_id, item.category_title): item for item in created_counts
    }
    open_map = {_category_key(item.category_id, item.category_title): item for item in open_counts}
    closed_map = {
        _category_key(item.category_id, item.category_title): item for item in closed_counts
    }
    feedback_map = {
        _category_key(item.category_id, item.category_title): item for item in feedback_stats
    }
    sla_map = {_category_key(item.category_id, item.category_title): item for item in sla_counts}
    category_keys = (
        set(created_map) | set(open_map) | set(closed_map) | set(feedback_map) | set(sla_map)
    )

    snapshots = []
    for key in category_keys:
        created = created_map.get(key)
        opened = open_map.get(key)
        closed = closed_map.get(key)
        feedback = feedback_map.get(key)
        sla = sla_map.get(key)
        category_id, category_title = key
        snapshots.append(
            AnalyticsCategorySnapshot(
                category_id=category_id,
                category_title=category_title,
                created_ticket_count=0 if created is None else created.ticket_count,
                open_ticket_count=0 if opened is None else opened.ticket_count,
                closed_ticket_count=0 if closed is None else closed.ticket_count,
                average_satisfaction=(
                    None
                    if feedback is None
                    else _normalize_average_rating(feedback.average_satisfaction)
                ),
                feedback_count=0 if feedback is None else feedback.feedback_count,
                sla_breach_count=0 if sla is None else sla.breach_count,
            )
        )

    return tuple(
        sorted(
            snapshots,
            key=lambda item: (
                item.created_ticket_count,
                item.open_ticket_count,
                item.category_title.lower(),
            ),
            reverse=True,
        )
    )


def _category_key(category_id: int | None, category_title: str | None) -> tuple[int | None, str]:
    if category_title:
        return category_id, category_title
    return category_id, "Без темы"
