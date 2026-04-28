from __future__ import annotations

import asyncio
from typing import Any, cast
from uuid import UUID

from application.contracts.actors import RequestActor
from application.use_cases.tickets.summaries import (
    OperatorTicketSummary,
    QueuedTicketSummary,
    TicketDetailsSummary,
)
from domain.enums.tickets import TicketStatus
from mini_app.serializers import (
    is_negative_dashboard_sentiment,
    needs_operator_reply,
    serialize_dashboard_bucket,
)


async def load_dashboard_ticket_details(
    *,
    client: Any,
    actor: RequestActor,
    tickets: list[QueuedTicketSummary | OperatorTicketSummary],
) -> dict[UUID, TicketDetailsSummary]:
    unique_ticket_ids = list(dict.fromkeys(ticket.public_id for ticket in tickets))
    if not unique_ticket_ids:
        return {}

    details = await asyncio.gather(
        *(
            safe_get_ticket_details(
                client=client,
                actor=actor,
                ticket_public_id=ticket_public_id,
            )
            for ticket_public_id in unique_ticket_ids
        )
    )
    return {item.public_id: item for item in details if item is not None}


async def safe_get_ticket_details(
    *,
    client: Any,
    actor: RequestActor,
    ticket_public_id: UUID,
) -> TicketDetailsSummary | None:
    try:
        return cast(
            TicketDetailsSummary | None,
            await client.get_ticket_details(ticket_public_id=ticket_public_id, actor=actor),
        )
    except Exception:  # noqa: BLE001
        return None


def build_operator_dashboard(
    *,
    queued: Any,
    mine: Any,
    ticket_details: dict[UUID, TicketDetailsSummary],
) -> dict[str, Any]:
    queue_records = [ticket_details.get(ticket.public_id, ticket) for ticket in queued]
    my_records = [ticket_details.get(ticket.public_id, ticket) for ticket in mine]
    visible_records = deduplicate_dashboard_tickets([*queue_records, *my_records])

    escalated_tickets = [
        ticket
        for ticket in visible_records
        if getattr(ticket, "status", None) == TicketStatus.ESCALATED
    ]
    tickets_without_category = [
        ticket
        for ticket in visible_records
        if not getattr(ticket, "category_title", None)
        and getattr(ticket, "category_id", None) is None
    ]
    negative_sentiment_tickets = [
        ticket for ticket in visible_records if is_negative_dashboard_sentiment(ticket)
    ]
    tickets_without_operator_reply = [
        ticket for ticket in my_records if needs_operator_reply(ticket)
    ]

    buckets = {
        "unassigned_open_tickets": serialize_dashboard_bucket(
            key="unassigned_open_tickets",
            label="Свободные заявки",
            tickets=list(queue_records),
            route="queue",
            empty_label="Свободных заявок сейчас нет.",
        ),
        "my_active_tickets": serialize_dashboard_bucket(
            key="my_active_tickets",
            label="Мои активные",
            tickets=list(my_records),
            route="mine",
            empty_label="У вас нет активных заявок.",
        ),
        "escalated_tickets": serialize_dashboard_bucket(
            key="escalated_tickets",
            label="Эскалации",
            tickets=escalated_tickets,
            route="mine",
            severity="critical",
            empty_label="Эскалаций в видимой зоне нет.",
        ),
        "sla_breached_tickets": serialize_dashboard_bucket(
            key="sla_breached_tickets",
            label="SLA нарушен",
            tickets=[],
            route="queue",
            severity="critical",
            empty_label="Живой SLA пока недоступен.",
            unavailable_reason=("Живой SLA пока не передаётся в рабочее место."),
        ),
        "sla_at_risk_tickets": serialize_dashboard_bucket(
            key="sla_at_risk_tickets",
            label="SLA в риске",
            tickets=[],
            route="queue",
            severity="warning",
            empty_label="Живой SLA пока недоступен.",
            unavailable_reason=("Живой SLA пока не передаётся в рабочее место."),
        ),
        "negative_sentiment_tickets": serialize_dashboard_bucket(
            key="negative_sentiment_tickets",
            label="Негативный тон",
            tickets=negative_sentiment_tickets,
            route="mine",
            severity="warning",
            empty_label="Негативных сигналов в видимой зоне нет.",
        ),
        "tickets_without_operator_reply": serialize_dashboard_bucket(
            key="tickets_without_operator_reply",
            label="Ждут моего ответа",
            tickets=tickets_without_operator_reply,
            route="mine",
            severity="warning",
            empty_label="Нет заявок, где сейчас нужен ваш ответ.",
        ),
        "tickets_without_category": serialize_dashboard_bucket(
            key="tickets_without_category",
            label="Без темы",
            tickets=tickets_without_category,
            route="queue",
            empty_label="Все видимые заявки размечены темами.",
        ),
    }
    return {
        "buckets": buckets,
        "sections": {
            "needs_attention": [
                "sla_breached_tickets",
                "sla_at_risk_tickets",
                "escalated_tickets",
                "negative_sentiment_tickets",
            ],
            "my_work": ["my_active_tickets", "tickets_without_operator_reply"],
            "queue": ["unassigned_open_tickets", "tickets_without_category"],
        },
    }


def deduplicate_dashboard_tickets(tickets: list[Any]) -> list[Any]:
    seen: set[UUID] = set()
    result: list[Any] = []
    for ticket in tickets:
        public_id = getattr(ticket, "public_id", None)
        if not isinstance(public_id, UUID) or public_id in seen:
            continue
        seen.add(public_id)
        result.append(ticket)
    return result
