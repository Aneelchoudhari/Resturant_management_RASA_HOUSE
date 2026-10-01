"""add staff roles, menu metadata, and cleaning tables

Revision ID: 0003
Revises: 0002
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE tablestatus ADD VALUE IF NOT EXISTS 'cleaning'")
    for role in ("manager", "waiter", "chef", "cashier", "inventory"):
        op.execute(f"ALTER TYPE staffrole ADD VALUE IF NOT EXISTS '{role}'")
    op.add_column("menu_items", sa.Column("description", sa.String(), nullable=True))
    op.add_column("menu_items", sa.Column("image_url", sa.String(), nullable=True))
    op.add_column("menu_items", sa.Column("available", sa.Integer(), nullable=False, server_default="1"))


def downgrade() -> None:
    op.drop_column("menu_items", "available")
    op.drop_column("menu_items", "image_url")
    op.drop_column("menu_items", "description")