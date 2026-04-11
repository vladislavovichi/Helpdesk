"""Add structured audit logs for sensitive operational actions.

Revision ID: 20260411_07
Revises: 20260410_06
Create Date: 2026-04-11 12:00:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20260411_07"
down_revision = "20260410_06"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("action", sa.String(length=120), nullable=False),
        sa.Column("entity_type", sa.String(length=80), nullable=False),
        sa.Column("outcome", sa.String(length=40), nullable=False),
        sa.Column("actor_telegram_user_id", sa.BigInteger(), nullable=True),
        sa.Column("entity_id", sa.BigInteger(), nullable=True),
        sa.Column("entity_public_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("correlation_id", sa.String(length=64), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_audit_logs")),
    )
    op.create_index(op.f("ix_audit_logs_action"), "audit_logs", ["action"], unique=False)
    op.create_index(
        op.f("ix_audit_logs_actor_telegram_user_id"),
        "audit_logs",
        ["actor_telegram_user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_audit_logs_correlation_id"),
        "audit_logs",
        ["correlation_id"],
        unique=False,
    )
    op.create_index(op.f("ix_audit_logs_created_at"), "audit_logs", ["created_at"], unique=False)
    op.create_index(op.f("ix_audit_logs_entity_id"), "audit_logs", ["entity_id"], unique=False)
    op.create_index(
        op.f("ix_audit_logs_entity_public_id"),
        "audit_logs",
        ["entity_public_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_audit_logs_entity_type"),
        "audit_logs",
        ["entity_type"],
        unique=False,
    )
    op.create_index(op.f("ix_audit_logs_outcome"), "audit_logs", ["outcome"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_audit_logs_outcome"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_entity_type"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_entity_public_id"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_entity_id"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_created_at"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_correlation_id"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_actor_telegram_user_id"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_action"), table_name="audit_logs")
    op.drop_table("audit_logs")
