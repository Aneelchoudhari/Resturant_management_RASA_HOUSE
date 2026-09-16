"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-09-16

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tables",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("number", sa.Integer(), nullable=False, unique=True),
        sa.Column("capacity", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("available", "occupied", "reserved", name="tablestatus"),
            nullable=False,
            server_default="available",
        ),
    )

    op.create_table(
        "staff",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column(
            "role",
            sa.Enum("staff", "admin", name="staffrole"),
            nullable=False,
            server_default="staff",
        ),
        sa.Column("email", sa.String(), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(), nullable=False),
    )

    op.create_table(
        "menu_items",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("category", sa.String(), nullable=False),
        sa.Column("price", sa.Float(), nullable=False),
        sa.Column("tags", sa.String(), nullable=True),
    )

    op.create_table(
        "reservations",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("table_id", sa.Integer(), sa.ForeignKey("tables.id"), nullable=True),
        sa.Column("guest_name", sa.String(), nullable=False),
        sa.Column("party_size", sa.Integer(), nullable=False),
        sa.Column("start_time", sa.DateTime(), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False, server_default="60"),
        sa.Column(
            "status",
            sa.Enum("pending", "confirmed", "cancelled", "completed", name="reservationstatus"),
            nullable=False,
            server_default="pending",
        ),
    )

    op.create_table(
        "waitlist_entries",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("guest_name", sa.String(), nullable=False),
        sa.Column("party_size", sa.Integer(), nullable=False),
        sa.Column("priority_tier", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("joined_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "orders",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("table_id", sa.Integer(), sa.ForeignKey("tables.id"), nullable=True),
        sa.Column(
            "status",
            sa.Enum("pending", "in_progress", "completed", "cancelled", name="orderstatus"),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("orders")
    op.drop_table("waitlist_entries")
    op.drop_table("reservations")
    op.drop_table("menu_items")
    op.drop_table("staff")
    op.drop_table("tables")
    op.execute("DROP TYPE IF EXISTS orderstatus")
    op.execute("DROP TYPE IF EXISTS reservationstatus")
    op.execute("DROP TYPE IF EXISTS tablestatus")
    op.execute("DROP TYPE IF EXISTS staffrole")
