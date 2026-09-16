from datetime import timedelta
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel
from app.database import get_db
from app import models
from app.dsa.interval_scheduler import (
    allocate,
    ReservationSlot,
    TableSlot,
)

router = APIRouter(prefix="/tables", tags=["tables"])


# ── response schemas ───────────────────────────────────────────────────────────

class AllocationAssignment(BaseModel):
    reservation_id: int
    table_id: int
    guest_name: str
    party_size: int
    start_time: str
    end_time: str
    table_number: int
    table_capacity: int


class AllocationResponse(BaseModel):
    assignments: List[AllocationAssignment]
    unassigned_reservation_ids: List[int]


# ── route ──────────────────────────────────────────────────────────────────────

@router.get("/allocate", response_model=AllocationResponse)
def get_allocation(db: Session = Depends(get_db)):
    """
    Run the greedy interval-scheduling allocator over all pending reservations
    and available tables. Returns the proposed assignment plan (read-only).
    """
    reservations = (
        db.query(models.Reservation)
        .filter(models.Reservation.status == models.ReservationStatus.pending)
        .all()
    )
    tables = (
        db.query(models.Table)
        .filter(models.Table.status == models.TableStatus.available)
        .all()
    )

    slots = [
        ReservationSlot(
            reservation_id=r.id,
            start=r.start_time.timestamp(),
            end=r.start_time.timestamp() + r.duration_minutes * 60,
            party_size=r.party_size,
        )
        for r in reservations
    ]
    table_slots = [TableSlot(table_id=t.id, capacity=t.capacity) for t in tables]

    result = allocate(slots, table_slots)

    # Build enriched response
    res_map = {r.id: r for r in reservations}
    table_map = {t.id: t for t in tables}

    enriched = []
    for a in result["assignments"]:
        r = res_map[a.reservation_id]
        t = table_map[a.table_id]
        enriched.append(
            AllocationAssignment(
                reservation_id=r.id,
                table_id=t.id,
                guest_name=r.guest_name,
                party_size=r.party_size,
                start_time=r.start_time.isoformat(),
                end_time=(r.start_time + timedelta(minutes=r.duration_minutes)).isoformat(),
                table_number=t.number,
                table_capacity=t.capacity,
            )
        )

    return AllocationResponse(
        assignments=enriched,
        unassigned_reservation_ids=result["unassigned"],
    )
