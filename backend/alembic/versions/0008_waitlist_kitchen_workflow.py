"""persist waitlist lifecycle and kitchen ticket workflow

Revision ID: 0008
Revises: 0007
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE TYPE waitliststatus AS ENUM ('waiting', 'seated', 'removed')")
    waitlist_status = postgresql.ENUM("waiting", "seated", "removed", name="waitliststatus", create_type=False)
    op.add_column(
        "waitlist_entries",
        sa.Column("status", waitlist_status, nullable=False, server_default="waiting"),
    )
    op.create_index(
        "ix_waitlist_entries_status_priority_joined",
        "waitlist_entries",
        ["status", "priority_tier", "joined_at"],
    )
    op.add_column("waitlist_entries", sa.Column("seated_table_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_waitlist_entries_seated_table_id_tables",
        "waitlist_entries",
        "tables",
        ["seated_table_id"],
        ["id"],
    )
    op.create_index("ix_waitlist_entries_seated_table_id", "waitlist_entries", ["seated_table_id"])

    op.add_column("orders", sa.Column("idempotency_key", sa.String(length=128), nullable=True))
    op.add_column("orders", sa.Column("idempotency_fingerprint", sa.String(length=64), nullable=True))
    op.create_unique_constraint("uq_orders_idempotency_key", "orders", ["idempotency_key"])

    op.create_table(
        "kitchen_routing_state",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("next_unknown_station", sa.Integer(), nullable=False, server_default="0"),
    )
    op.execute("INSERT INTO kitchen_routing_state (id, next_unknown_station) VALUES (1, 0)")

    op.execute("CREATE TYPE kitchenticketstatus AS ENUM ('queued', 'claimed', 'processing', 'completed', 'cancelled')")
    ticket_status = postgresql.ENUM(
        "queued", "claimed", "processing", "completed", "cancelled",
        name="kitchenticketstatus",
        create_type=False,
    )
    op.create_table(
        "kitchen_tickets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("order_item_id", sa.Integer(), sa.ForeignKey("order_items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("unit_number", sa.Integer(), nullable=False),
        sa.Column("station", sa.String(length=16), nullable=False),
        sa.Column("status", ticket_status, nullable=False, server_default="queued"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("claimed_by_staff_id", sa.Integer(), sa.ForeignKey("staff.id", ondelete="SET NULL"), nullable=True),
        sa.Column("claimed_at", sa.DateTime(), nullable=True),
        sa.Column("processing_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.CheckConstraint("unit_number > 0", name="ck_kitchen_ticket_unit_positive"),
        sa.CheckConstraint("station IN ('grill', 'dessert', 'drinks', 'sides')", name="ck_kitchen_ticket_station_valid"),
        sa.UniqueConstraint("order_item_id", "unit_number", name="uq_kitchen_ticket_order_item_unit"),
    )
    op.create_index("ix_kitchen_tickets_station_status_id", "kitchen_tickets", ["station", "status", "id"])
    op.create_index("ix_kitchen_tickets_claimed_by", "kitchen_tickets", ["claimed_by_staff_id"])

    bind = op.get_bind()
    routing_map = {
        "mains": "grill",
        "grills": "grill",
        "starters": "grill",
        "desserts": "dessert",
        "dessert": "dessert",
        "drinks": "drinks",
        "beverages": "drinks",
        "sides": "sides",
        "side": "sides",
    }
    stations = ("grill", "dessert", "drinks", "sides")
    cursor = 0
    active_items = bind.execute(
        sa.text(
            """
            SELECT oi.id, oi.quantity, mi.category
            FROM order_items oi
            JOIN menu_items mi ON mi.id = oi.menu_item_id
            JOIN orders o ON o.id = oi.order_id
            WHERE o.status IN ('placed', 'accepted', 'preparing', 'pending', 'in_progress')
            ORDER BY o.created_at, o.id, oi.id
            """
        )
    )
    for item in active_items:
        mapped_station = routing_map.get(item.category.lower())
        for unit_number in range(1, item.quantity + 1):
            station = mapped_station
            if station is None:
                station = stations[cursor % len(stations)]
                cursor += 1
            bind.execute(
                sa.text(
                    "INSERT INTO kitchen_tickets (order_item_id, unit_number, station, status, created_at) "
                    "VALUES (:order_item_id, :unit_number, :station, 'queued', CURRENT_TIMESTAMP)"
                ),
                {"order_item_id": item.id, "unit_number": unit_number, "station": station},
            )
    bind.execute(
        sa.text("UPDATE kitchen_routing_state SET next_unknown_station = :cursor WHERE id = 1"),
        {"cursor": cursor},
    )


def downgrade() -> None:
    op.drop_index("ix_kitchen_tickets_claimed_by", table_name="kitchen_tickets")
    op.drop_index("ix_kitchen_tickets_station_status_id", table_name="kitchen_tickets")
    op.drop_table("kitchen_tickets")
    op.execute("DROP TYPE kitchenticketstatus")
    op.drop_table("kitchen_routing_state")
    op.drop_constraint("uq_orders_idempotency_key", "orders", type_="unique")
    op.drop_column("orders", "idempotency_fingerprint")
    op.drop_column("orders", "idempotency_key")
    op.drop_index("ix_waitlist_entries_status_priority_joined", table_name="waitlist_entries")
    op.drop_index("ix_waitlist_entries_seated_table_id", table_name="waitlist_entries")
    op.drop_constraint("fk_waitlist_entries_seated_table_id_tables", "waitlist_entries", type_="foreignkey")
    op.drop_column("waitlist_entries", "seated_table_id")
    op.drop_column("waitlist_entries", "status")
    op.execute("DROP TYPE waitliststatus")