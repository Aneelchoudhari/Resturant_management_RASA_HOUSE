"""add customer ordering and payment fields

Revision ID: 0004
Revises: 0003
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    for value in ("placed", "accepted", "preparing", "ready", "served"):
        op.execute(f"ALTER TYPE orderstatus ADD VALUE IF NOT EXISTS '{value}'")
    op.execute("CREATE TYPE paymentstatus AS ENUM ('pending', 'paid', 'failed', 'refunded')")
    op.execute("CREATE TYPE paymentmethod AS ENUM ('upi', 'card', 'cash')")
    op.add_column("orders", sa.Column("customer_id", sa.Integer(), sa.ForeignKey("customers.id"), nullable=True))
    op.add_column("orders", sa.Column("order_type", sa.String(), nullable=False, server_default="dine_in"))
    op.add_column("orders", sa.Column("special_instructions", sa.String(), nullable=True))
    op.add_column("orders", sa.Column("total_amount", sa.Float(), nullable=False, server_default="0"))
    op.add_column("orders", sa.Column("payment_status", sa.Enum("pending", "paid", "failed", "refunded", name="paymentstatus"), nullable=False, server_default="pending"))
    op.add_column("orders", sa.Column("payment_method", sa.Enum("upi", "card", "cash", name="paymentmethod"), nullable=True))
    op.create_table(
        "order_items",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id"), nullable=False),
        sa.Column("menu_item_id", sa.Integer(), sa.ForeignKey("menu_items.id"), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("unit_price", sa.Float(), nullable=False),
        sa.Column("special_instructions", sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("order_items")
    op.drop_column("orders", "payment_method")
    op.drop_column("orders", "payment_status")
    op.drop_column("orders", "total_amount")
    op.drop_column("orders", "special_instructions")
    op.drop_column("orders", "order_type")
    op.drop_column("orders", "customer_id")
    op.execute("DROP TYPE paymentmethod")
    op.execute("DROP TYPE paymentstatus")