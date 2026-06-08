"""google calendar two-way sync

Revision ID: 0004
Revises: 0003
Create Date: 2026-06-08
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # calendar_sources: make ical_url nullable
    op.alter_column("calendar_sources", "ical_url", nullable=True, schema="calendar")

    # calendar_sources: add new columns
    op.add_column(
        "calendar_sources",
        sa.Column("source_type", sa.String(16), nullable=False, server_default="ical"),
        schema="calendar",
    )
    op.add_column(
        "calendar_sources",
        sa.Column("google_calendar_id", sa.Text(), nullable=True),
        schema="calendar",
    )
    op.add_column(
        "calendar_sources",
        sa.Column("google_credentials", JSONB(), nullable=True),
        schema="calendar",
    )

    # events: add new columns
    op.add_column(
        "events",
        sa.Column("google_event_id", sa.String(512), nullable=True),
        schema="calendar",
    )
    op.add_column(
        "events",
        sa.Column("google_color_id", sa.String(16), nullable=True),
        schema="calendar",
    )
    op.add_column(
        "events",
        sa.Column("reminder_minutes", sa.Integer(), nullable=True),
        schema="calendar",
    )

    # new google_oauth_sessions table
    op.create_table(
        "google_oauth_sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("session_token", sa.String(128), nullable=False, unique=True),
        sa.Column("credentials_json", sa.Text(), nullable=True),
        sa.Column("calendar_list_json", sa.Text(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        schema="calendar",
    )
    op.create_index(
        "ix_calendar_google_oauth_sessions_session_token",
        "google_oauth_sessions",
        ["session_token"],
        schema="calendar",
    )


def downgrade() -> None:
    op.drop_table("google_oauth_sessions", schema="calendar")
    op.drop_column("events", "reminder_minutes", schema="calendar")
    op.drop_column("events", "google_color_id", schema="calendar")
    op.drop_column("events", "google_event_id", schema="calendar")
    op.drop_column("calendar_sources", "google_credentials", schema="calendar")
    op.drop_column("calendar_sources", "google_calendar_id", schema="calendar")
    op.drop_column("calendar_sources", "source_type", schema="calendar")
    op.alter_column("calendar_sources", "ical_url", nullable=False, schema="calendar")
