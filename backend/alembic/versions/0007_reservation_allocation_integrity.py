"""enforce reservation and table allocation integrity

Revision ID: 0007
Revises: 0006
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")

    op.add_column("tables", sa.Column("current_customer_id", sa.Integer(), nullable=True))
    op.add_column("tables", sa.Column("current_guest_name", sa.String(length=200), nullable=True))
    op.add_column("tables", sa.Column("current_party_size", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_tables_current_customer_id_customers",
        "tables",
        "customers",
        ["current_customer_id"],
        ["id"],
    )
    op.create_check_constraint("ck_tables_capacity_positive", "tables", "capacity > 0")
    op.create_check_constraint(
        "ck_tables_current_party_size_positive",
        "tables",
        "current_party_size IS NULL OR current_party_size > 0",
    )

    op.add_column("reservations", sa.Column("idempotency_key", sa.String(length=128), nullable=True))
    op.create_unique_constraint("uq_reservations_idempotency_key", "reservations", ["idempotency_key"])
    op.create_check_constraint("ck_reservations_party_size_positive", "reservations", "party_size > 0")
    op.create_check_constraint("ck_reservations_duration_positive", "reservations", "duration_minutes > 0")
    op.create_index(
        "ix_reservations_table_status_start",
        "reservations",
        ["table_id", "status", "start_time"],
    )
    op.execute(
        """
        ALTER TABLE reservations
        ADD CONSTRAINT ex_reservations_no_active_table_overlap
        EXCLUDE USING gist (
            table_id WITH =,
            tsrange(start_time, start_time + duration_minutes * interval '1 minute', '[)') WITH &&
        )
        WHERE (table_id IS NOT NULL AND status IN ('pending', 'confirmed'))
        """
    )

    op.add_column("waitlist_entries", sa.Column("reservation_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_waitlist_entries_reservation_id_reservations",
        "waitlist_entries",
        "reservations",
        ["reservation_id"],
        ["id"],
    )
    op.create_unique_constraint("uq_waitlist_entries_reservation_id", "waitlist_entries", ["reservation_id"])


def downgrade() -> None:
    op.drop_constraint("uq_waitlist_entries_reservation_id", "waitlist_entries", type_="unique")
    op.drop_constraint("fk_waitlist_entries_reservation_id_reservations", "waitlist_entries", type_="foreignkey")
    op.drop_column("waitlist_entries", "reservation_id")

    op.drop_constraint("ex_reservations_no_active_table_overlap", "reservations", type_="exclude")
    op.drop_index("ix_reservations_table_status_start", table_name="reservations")
    op.drop_constraint("ck_reservations_duration_positive", "reservations", type_="check")
    op.drop_constraint("ck_reservations_party_size_positive", "reservations", type_="check")
    op.drop_constraint("uq_reservations_idempotency_key", "reservations", type_="unique")
    op.drop_column("reservations", "idempotency_key")

    op.drop_constraint("ck_tables_current_party_size_positive", "tables", type_="check")
    op.drop_constraint("ck_tables_capacity_positive", "tables", type_="check")
    op.drop_constraint("fk_tables_current_customer_id_customers", "tables", type_="foreignkey")
    op.drop_column("tables", "current_party_size")
    op.drop_column("tables", "current_guest_name")
    op.drop_column("tables", "current_customer_id")