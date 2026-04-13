# mypy: disable-error-code="attr-defined,name-defined"
from __future__ import annotations

from application.services.stats import (
    AnalyticsCategorySnapshot,
    AnalyticsOperatorSnapshot,
    AnalyticsRatingBucket,
    AnalyticsWindow,
    HelpdeskAnalyticsSnapshot,
    OperatorTicketLoad,
)
from application.use_cases.analytics.exports import (
    AnalyticsExportFormat,
    AnalyticsSection,
    AnalyticsSnapshotExport,
)
from backend.grpc.generated import helpdesk_pb2
from backend.grpc.translators_shared import _has


def serialize_analytics_export(
    export: AnalyticsSnapshotExport,
) -> helpdesk_pb2.AnalyticsReportExport:
    return helpdesk_pb2.AnalyticsReportExport(
        format=export.format.value,
        filename=export.filename,
        content_type=export.content_type,
        content=export.content,
        section=export.section.value,
        window=export.window.value,
    )


def deserialize_analytics_export(
    export: helpdesk_pb2.AnalyticsReportExport,
) -> AnalyticsSnapshotExport:
    return AnalyticsSnapshotExport(
        format=AnalyticsExportFormat(export.format),
        filename=export.filename,
        content_type=export.content_type,
        content=export.content,
        section=AnalyticsSection(export.section),
        window=AnalyticsWindow(export.window),
    )


def serialize_analytics_snapshot(
    snapshot: HelpdeskAnalyticsSnapshot,
) -> helpdesk_pb2.HelpdeskAnalyticsSnapshot:
    message = helpdesk_pb2.HelpdeskAnalyticsSnapshot(
        window=snapshot.window.value,
        total_open_tickets=snapshot.total_open_tickets,
        queued_tickets_count=snapshot.queued_tickets_count,
        assigned_tickets_count=snapshot.assigned_tickets_count,
        escalated_tickets_count=snapshot.escalated_tickets_count,
        closed_tickets_count=snapshot.closed_tickets_count,
        period_created_tickets_count=snapshot.period_created_tickets_count,
        period_closed_tickets_count=snapshot.period_closed_tickets_count,
        feedback_count=snapshot.feedback_count,
        first_response_breach_count=snapshot.first_response_breach_count,
        resolution_breach_count=snapshot.resolution_breach_count,
    )
    if snapshot.average_first_response_time_seconds is not None:
        message.average_first_response_time_seconds = snapshot.average_first_response_time_seconds
    if snapshot.average_resolution_time_seconds is not None:
        message.average_resolution_time_seconds = snapshot.average_resolution_time_seconds
    if snapshot.satisfaction_average is not None:
        message.satisfaction_average = snapshot.satisfaction_average
    if snapshot.feedback_coverage_percent is not None:
        message.feedback_coverage_percent = snapshot.feedback_coverage_percent
    message.tickets_per_operator.extend(
        serialize_operator_ticket_load(item) for item in snapshot.tickets_per_operator
    )
    message.rating_distribution.extend(
        serialize_rating_bucket(item) for item in snapshot.rating_distribution
    )
    message.operator_snapshots.extend(
        serialize_operator_snapshot(item) for item in snapshot.operator_snapshots
    )
    message.category_snapshots.extend(
        serialize_category_snapshot(item) for item in snapshot.category_snapshots
    )
    message.best_operators_by_closures.extend(
        serialize_operator_snapshot(item) for item in snapshot.best_operators_by_closures
    )
    message.best_operators_by_satisfaction.extend(
        serialize_operator_snapshot(item) for item in snapshot.best_operators_by_satisfaction
    )
    message.top_categories.extend(
        serialize_category_snapshot(item) for item in snapshot.top_categories
    )
    message.sla_categories.extend(
        serialize_category_snapshot(item) for item in snapshot.sla_categories
    )
    return message


def deserialize_analytics_snapshot(
    snapshot: helpdesk_pb2.HelpdeskAnalyticsSnapshot,
) -> HelpdeskAnalyticsSnapshot:
    return HelpdeskAnalyticsSnapshot(
        window=AnalyticsWindow(snapshot.window),
        total_open_tickets=snapshot.total_open_tickets,
        queued_tickets_count=snapshot.queued_tickets_count,
        assigned_tickets_count=snapshot.assigned_tickets_count,
        escalated_tickets_count=snapshot.escalated_tickets_count,
        closed_tickets_count=snapshot.closed_tickets_count,
        tickets_per_operator=tuple(
            deserialize_operator_ticket_load(item) for item in snapshot.tickets_per_operator
        ),
        period_created_tickets_count=snapshot.period_created_tickets_count,
        period_closed_tickets_count=snapshot.period_closed_tickets_count,
        average_first_response_time_seconds=(
            snapshot.average_first_response_time_seconds
            if _has(snapshot, "average_first_response_time_seconds")
            else None
        ),
        average_resolution_time_seconds=(
            snapshot.average_resolution_time_seconds
            if _has(snapshot, "average_resolution_time_seconds")
            else None
        ),
        satisfaction_average=(
            snapshot.satisfaction_average if _has(snapshot, "satisfaction_average") else None
        ),
        feedback_count=snapshot.feedback_count,
        feedback_coverage_percent=(
            snapshot.feedback_coverage_percent
            if _has(snapshot, "feedback_coverage_percent")
            else None
        ),
        rating_distribution=tuple(
            deserialize_rating_bucket(item) for item in snapshot.rating_distribution
        ),
        operator_snapshots=tuple(
            deserialize_operator_snapshot(item) for item in snapshot.operator_snapshots
        ),
        category_snapshots=tuple(
            deserialize_category_snapshot(item) for item in snapshot.category_snapshots
        ),
        best_operators_by_closures=tuple(
            deserialize_operator_snapshot(item) for item in snapshot.best_operators_by_closures
        ),
        best_operators_by_satisfaction=tuple(
            deserialize_operator_snapshot(item) for item in snapshot.best_operators_by_satisfaction
        ),
        top_categories=tuple(
            deserialize_category_snapshot(item) for item in snapshot.top_categories
        ),
        first_response_breach_count=snapshot.first_response_breach_count,
        resolution_breach_count=snapshot.resolution_breach_count,
        sla_categories=tuple(
            deserialize_category_snapshot(item) for item in snapshot.sla_categories
        ),
    )


def serialize_operator_ticket_load(
    item: OperatorTicketLoad,
) -> helpdesk_pb2.OperatorTicketLoad:
    return helpdesk_pb2.OperatorTicketLoad(
        operator_id=item.operator_id,
        display_name=item.display_name,
        ticket_count=item.ticket_count,
    )


def deserialize_operator_ticket_load(
    item: helpdesk_pb2.OperatorTicketLoad,
) -> OperatorTicketLoad:
    return OperatorTicketLoad(
        operator_id=item.operator_id,
        display_name=item.display_name,
        ticket_count=item.ticket_count,
    )


def serialize_rating_bucket(
    item: AnalyticsRatingBucket,
) -> helpdesk_pb2.AnalyticsRatingBucket:
    return helpdesk_pb2.AnalyticsRatingBucket(rating=item.rating, count=item.count)


def deserialize_rating_bucket(
    item: helpdesk_pb2.AnalyticsRatingBucket,
) -> AnalyticsRatingBucket:
    return AnalyticsRatingBucket(rating=item.rating, count=item.count)


def serialize_operator_snapshot(
    item: AnalyticsOperatorSnapshot,
) -> helpdesk_pb2.AnalyticsOperatorSnapshot:
    message = helpdesk_pb2.AnalyticsOperatorSnapshot(
        operator_id=item.operator_id,
        display_name=item.display_name,
        active_ticket_count=item.active_ticket_count,
        closed_ticket_count=item.closed_ticket_count,
        feedback_count=item.feedback_count,
    )
    if item.average_first_response_time_seconds is not None:
        message.average_first_response_time_seconds = item.average_first_response_time_seconds
    if item.average_resolution_time_seconds is not None:
        message.average_resolution_time_seconds = item.average_resolution_time_seconds
    if item.average_satisfaction is not None:
        message.average_satisfaction = item.average_satisfaction
    return message


def deserialize_operator_snapshot(
    item: helpdesk_pb2.AnalyticsOperatorSnapshot,
) -> AnalyticsOperatorSnapshot:
    return AnalyticsOperatorSnapshot(
        operator_id=item.operator_id,
        display_name=item.display_name,
        active_ticket_count=item.active_ticket_count,
        closed_ticket_count=item.closed_ticket_count,
        average_first_response_time_seconds=(
            item.average_first_response_time_seconds
            if _has(item, "average_first_response_time_seconds")
            else None
        ),
        average_resolution_time_seconds=(
            item.average_resolution_time_seconds
            if _has(item, "average_resolution_time_seconds")
            else None
        ),
        average_satisfaction=(
            item.average_satisfaction if _has(item, "average_satisfaction") else None
        ),
        feedback_count=item.feedback_count,
    )


def serialize_category_snapshot(
    item: AnalyticsCategorySnapshot,
) -> helpdesk_pb2.AnalyticsCategorySnapshot:
    message = helpdesk_pb2.AnalyticsCategorySnapshot(
        category_title=item.category_title,
        created_ticket_count=item.created_ticket_count,
        open_ticket_count=item.open_ticket_count,
        closed_ticket_count=item.closed_ticket_count,
        feedback_count=item.feedback_count,
        sla_breach_count=item.sla_breach_count,
    )
    if item.category_id is not None:
        message.category_id = item.category_id
    if item.average_satisfaction is not None:
        message.average_satisfaction = item.average_satisfaction
    return message


def deserialize_category_snapshot(
    item: helpdesk_pb2.AnalyticsCategorySnapshot,
) -> AnalyticsCategorySnapshot:
    return AnalyticsCategorySnapshot(
        category_id=item.category_id if _has(item, "category_id") else None,
        category_title=item.category_title,
        created_ticket_count=item.created_ticket_count,
        open_ticket_count=item.open_ticket_count,
        closed_ticket_count=item.closed_ticket_count,
        average_satisfaction=(
            item.average_satisfaction if _has(item, "average_satisfaction") else None
        ),
        feedback_count=item.feedback_count,
        sla_breach_count=item.sla_breach_count,
    )
