"""persist table adjacency and index DSA-backed API queries

Revision ID: 0009
Revises: 0008
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0009"
down_revision: Union[str, None] = "0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE INDEX ix_menu_items_name_lower ON menu_items (lower(name) varchar_pattern_ops)")
    op.execute("CREATE INDEX ix_menu_items_category_lower ON menu_items (lower(category))")
    op.execute(
        "CREATE INDEX ix_waitlist_entries_active_score "
        "ON waitlist_entries (status, "
        "(priority_tier * 1000 + EXTRACT(EPOCH FROM joined_at) - party_size * 5), id)"
    )
    op.create_index("ix_orders_created_at_id", "orders", ["created_at", "id"])
    op.create_table(
        "table_adjacencies",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("table_id_low", sa.Integer(), sa.ForeignKey("tables.id", ondelete="CASCADE"), nullable=False),
        sa.Column("table_id_high", sa.Integer(), sa.ForeignKey("tables.id", ondelete="CASCADE"), nullable=False),
        sa.CheckConstraint("table_id_low < table_id_high", name="ck_table_adjacency_canonical_order"),
        sa.UniqueConstraint("table_id_low", "table_id_high", name="uq_table_adjacency_pair"),
    )
    op.create_index("ix_table_adjacencies_high", "table_adjacencies", ["table_id_high"])


def downgrade() -> None:
    op.drop_index("ix_table_adjacencies_high", table_name="table_adjacencies")
    op.drop_table("table_adjacencies")
    op.drop_index("ix_orders_created_at_id", table_name="orders")
    op.execute("DROP INDEX ix_waitlist_entries_active_score")
    op.execute("DROP INDEX ix_menu_items_category_lower")
    op.execute("DROP INDEX ix_menu_items_name_lower")