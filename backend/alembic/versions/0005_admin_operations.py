"""add admin operations, inventory, and audit logging

Revision ID: 0005
Revises: 0004
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE staffrole ADD VALUE IF NOT EXISTS 'receptionist'")
    op.add_column("staff", sa.Column("active", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("menu_items", sa.Column("stock_quantity", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("menu_items", sa.Column("low_stock_threshold", sa.Integer(), nullable=False, server_default="5"))
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("staff_id", sa.Integer(), sa.ForeignKey("staff.id"), nullable=True),
        sa.Column("staff_name", sa.String(), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("entity_type", sa.String(), nullable=True),
        sa.Column("entity_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_column("menu_items", "low_stock_threshold")
    op.drop_column("menu_items", "stock_quantity")
    op.drop_column("staff", "active")