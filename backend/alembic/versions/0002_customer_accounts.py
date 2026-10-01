"""add customer accounts and reservation ownership

Revision ID: 0002
Revises: 0001
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "customers",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(), nullable=False),
        sa.Column("loyalty_points", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "reservations",
        sa.Column("customer_id", sa.Integer(), sa.ForeignKey("customers.id"), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("reservations", "customer_id")
    op.drop_table("customers")