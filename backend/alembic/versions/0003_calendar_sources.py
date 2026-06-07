"""calendar sources

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-07
"""
from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "calendar_sources",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("ical_url", sa.Text(), nullable=False),
        sa.Column("color", sa.String(7), nullable=False, server_default="#eab308"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        schema="calendar",
    )
    op.add_column(
        "events",
        sa.Column("source_id", sa.Integer(), nullable=True),
        schema="calendar",
    )
    op.create_foreign_key(
        "fk_events_source_id",
        "events",
        "calendar_sources",
        ["source_id"],
        ["id"],
        source_schema="calendar",
        referent_schema="calendar",
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint("fk_events_source_id", "events", schema="calendar", type_="foreignkey")
    op.drop_column("events", "source_id", schema="calendar")
    op.drop_table("calendar_sources", schema="calendar")
