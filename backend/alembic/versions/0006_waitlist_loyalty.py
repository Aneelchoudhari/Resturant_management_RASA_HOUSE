"""add customer_id and entry_type to waitlist_entries

Revision ID: 0006
Revises: 0005
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add customer_id FK (nullable — walk-in guests have no account)
    op.add_column(
        "waitlist_entries",
        sa.Column("customer_id", sa.Integer(), sa.ForeignKey("customers.id"), nullable=True),
    )
    # Add entry_type with a default so all existing rows become 'walk_in'
    op.add_column(
        "waitlist_entries",
        sa.Column("entry_type", sa.String(), nullable=False, server_default="walk_in"),
    )


def downgrade() -> None:
    op.drop_column("waitlist_entries", "entry_type")
    op.drop_column("waitlist_entries", "customer_id")
