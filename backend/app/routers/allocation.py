from datetime import timedelta, timezone
from fastapi import APIRouter, Depends
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel
from app.database import get_db
from app import models, schemas
from app.auth import require_roles
from app.reservation_rules import ensure_table_interval_available
from app.dsa.interval_scheduler import (
    allocate,
    ReservationSlot,
    TableSlot,
)

router = APIRouter(prefix="/tables", tags=["tables"])

# Only admin, manager, and receptionist (host) can run table allocation
ALLOCATION_ROLES = (
    models.StaffRole.admin,
    models.StaffRole.manager,
    models.StaffRole.receptionist,  # host/floor manager
)


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


def _ensure_reservation_table_is_free(db: Session, reservation: models.Reservation, table: models.Table) -> None:
    ensure_table_interval_available(
        db,
        table.id,
        reservation.start_time,
        reservation.start_time + timedelta(minutes=reservation.duration_minutes),
        exclude_reservation_id=reservation.id,
    )


# ── route ──────────────────────────────────────────────────────────────────────

@router.get("/allocate", response_model=AllocationResponse)
def get_allocation(
    db: Session = Depends(get_db),
    _: models.Staff = Depends(require_roles(*ALLOCATION_ROLES)),
):
    """
    Return a read-only proposal for unassigned pending/confirmed reservations.
    Restricted to admin, manager, and host (receptionist) roles.
    """
    active_reservations = (
        db.query(models.Reservation)
        .filter(models.Reservation.status.in_((models.ReservationStatus.pending, models.ReservationStatus.confirmed)))
        .all()
    )
    tables = (
        db.query(models.Table)
        .filter(models.Table.status == models.TableStatus.available)
        .all()
    )

    reservations = [reservation for reservation in active_reservations if reservation.table_id is None]
    table_ids = {table.id for table in tables}
    blocked_intervals = {}
    for reservation in active_reservations:
        if reservation.table_id in table_ids:
            start = reservation.start_time.replace(tzinfo=timezone.utc).timestamp()
            end = start + reservation.duration_minutes * 60
            blocked_intervals.setdefault(reservation.table_id, []).append((start, end))

    slots = [
        ReservationSlot(
            reservation_id=r.id,
            start=r.start_time.replace(tzinfo=timezone.utc).timestamp(),
            end=r.start_time.replace(tzinfo=timezone.utc).timestamp() + r.duration_minutes * 60,
            party_size=r.party_size,
        )
        for r in reservations
    ]
    table_slots = [TableSlot(table_id=t.id, capacity=t.capacity) for t in tables]

    result = allocate(slots, table_slots, existing_assignments=blocked_intervals)

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


@router.post("/allocate", response_model=List[schemas.ReservationResponse])
def commit_allocation(
    payload: schemas.AllocationPlanCommitRequest,
    db: Session = Depends(get_db),
    _: models.Staff = Depends(require_roles(*ALLOCATION_ROLES)),
):
    """Persist an assignment plan atomically; repeated identical assignments are safe."""
    reservation_ids = sorted({item.reservation_id for item in payload.assignments})
    reservation_rows = {
        reservation.id: reservation
        for reservation in db.query(models.Reservation)
        .filter(models.Reservation.id.in_(reservation_ids))
        .all()
    }
    if len(reservation_rows) != len(reservation_ids):
        raise HTTPException(status_code=404, detail="Reservation not found")
    if any(
        reservation_rows[item.reservation_id].table_id not in (None, item.table_id)
        for item in payload.assignments
    ):
        raise HTTPException(status_code=409, detail="Reservation is already assigned to another table")

    table_ids = sorted({item.table_id for item in payload.assignments})
    tables = {}
    for table_id in table_ids:
        table = db.query(models.Table).filter(models.Table.id == table_id).with_for_update().first()
        if not table:
            raise HTTPException(status_code=404, detail="Table not found")
        tables[table_id] = table

    reservations = {}
    for reservation_id in reservation_ids:
        reservation = db.query(models.Reservation).filter(
            models.Reservation.id == reservation_id
        ).with_for_update().first()
        if not reservation:
            raise HTTPException(status_code=404, detail="Reservation not found")
        reservations[reservation_id] = reservation

    try:
        for item in payload.assignments:
            reservation = reservations[item.reservation_id]
            table = tables[item.table_id]
            if reservation.status not in (models.ReservationStatus.pending, models.ReservationStatus.confirmed):
                raise HTTPException(status_code=409, detail="Only pending or confirmed reservations can be allocated")
            if reservation.table_id not in (None, table.id):
                raise HTTPException(status_code=409, detail="Reservation is already assigned to another table")
            if table.status != models.TableStatus.available:
                raise HTTPException(status_code=409, detail="Table is not available for reservation allocation")
            if table.capacity < reservation.party_size:
                raise HTTPException(status_code=422, detail="Party size exceeds table capacity")
            _ensure_reservation_table_is_free(db, reservation, table)
            if reservation.table_id is None:
                reservation.table_id = table.id
                db.flush()
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Allocation conflicts with an existing reservation") from exc

    return [reservations[item.reservation_id] for item in payload.assignments]
