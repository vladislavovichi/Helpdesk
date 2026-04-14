"""Add ticket sentiment signals and client duplicate collapse metadata.

Revision ID: 20260413_11
Revises: 20260413_10
Create Date: 2026-04-13 18:10:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20260413_11"
down_revision = "20260413_10"
branch_labels = None
depends_on = None


ticket_sentiment = postgresql.ENUM(
    "calm",
    "frustrated",
    "escalation_risk",
    name="ticket_sentiment",
    create_type=False,
)
ticket_signal_confidence = postgresql.ENUM(
    "low",
    "medium",
    "high",
    name="ticket_signal_confidence",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    ticket_sentiment.create(bind, checkfirst=True)
    ticket_signal_confidence.create(bind, checkfirst=True)

    op.execute(
        "ALTER TYPE ticket_event_type ADD VALUE IF NOT EXISTS 'client_message_duplicate_collapsed'"
    )
    op.execute("ALTER TYPE ticket_event_type ADD VALUE IF NOT EXISTS 'client_sentiment_flagged'")

    op.add_column("tickets", sa.Column("sentiment", ticket_sentiment, nullable=True))
    op.add_column(
        "tickets",
        sa.Column("sentiment_confidence", ticket_signal_confidence, nullable=True),
    )
    op.add_column("tickets", sa.Column("sentiment_reason", sa.String(length=255), nullable=True))
    op.add_column(
        "tickets",
        sa.Column("sentiment_detected_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(op.f("ix_tickets_sentiment"), "tickets", ["sentiment"], unique=False)

    op.add_column("ticket_messages", sa.Column("sentiment", ticket_sentiment, nullable=True))
    op.add_column(
        "ticket_messages",
        sa.Column("sentiment_confidence", ticket_signal_confidence, nullable=True),
    )
    op.add_column(
        "ticket_messages",
        sa.Column("sentiment_reason", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "ticket_messages",
        sa.Column(
            "duplicate_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )
    op.add_column(
        "ticket_messages",
        sa.Column("last_duplicate_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        op.f("ix_ticket_messages_sentiment"),
        "ticket_messages",
        ["sentiment"],
        unique=False,
    )


def downgrade() -> None:
    bind = op.get_bind()

    op.drop_index(op.f("ix_ticket_messages_sentiment"), table_name="ticket_messages")
    op.drop_column("ticket_messages", "last_duplicate_at")
    op.drop_column("ticket_messages", "duplicate_count")
    op.drop_column("ticket_messages", "sentiment_reason")
    op.drop_column("ticket_messages", "sentiment_confidence")
    op.drop_column("ticket_messages", "sentiment")

    op.drop_index(op.f("ix_tickets_sentiment"), table_name="tickets")
    op.drop_column("tickets", "sentiment_detected_at")
    op.drop_column("tickets", "sentiment_reason")
    op.drop_column("tickets", "sentiment_confidence")
    op.drop_column("tickets", "sentiment")

    ticket_signal_confidence.drop(bind, checkfirst=True)
    ticket_sentiment.drop(bind, checkfirst=True)

    op.execute(
        "ALTER TYPE ticket_event_type RENAME TO ticket_event_type_with_support_signals"
    )
    op.execute(
        "CREATE TYPE ticket_event_type AS ENUM ("
        "'created',"
        "'queued',"
        "'status_changed',"
        "'assigned',"
        "'reassigned',"
        "'auto_reassigned',"
        "'message_added',"
        "'client_message_added',"
        "'operator_message_added',"
        "'tag_added',"
        "'tag_removed',"
        "'escalated',"
        "'auto_escalated',"
        "'sla_breached_first_response',"
        "'sla_breached_resolution',"
        "'closed'"
        ")"
    )
    op.execute(
        "ALTER TABLE ticket_events "
        "ALTER COLUMN event_type "
        "TYPE ticket_event_type "
        "USING event_type::text::ticket_event_type"
    )
    op.execute("DROP TYPE ticket_event_type_with_support_signals")
