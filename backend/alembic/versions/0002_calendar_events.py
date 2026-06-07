"""calendar events

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-07
"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS calendar")
    op.create_table(
        "events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("uid", sa.String(512), nullable=False),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("start_dt", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_dt", sa.DateTime(timezone=True), nullable=False),
        sa.Column("all_day", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("location", sa.String(512), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("source", sa.String(32), nullable=False, server_default="ical"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uid"),
        schema="calendar",
    )
    op.create_index("ix_calendar_events_uid", "events", ["uid"], schema="calendar")
    op.create_index("ix_calendar_events_start_dt", "events", ["start_dt"], schema="calendar")


def downgrade() -> None:
    op.drop_table("events", schema="calendar")
    op.execute("DROP SCHEMA IF EXISTS calendar")
