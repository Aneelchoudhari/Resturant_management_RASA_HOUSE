from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from sqlalchemy import extract
from sqlalchemy.exc import IntegrityError
from app.database import get_db
from app import models, schemas
from app.auth import get_current_staff, require_roles
from app.reservation_rules import ACTIVE_RESERVATION_STATUSES, ensure_table_interval_available

router = APIRouter(prefix="/waitlist", tags=["waitlist"])

# Roles that can add VIP and Reservation entries (require staff auth)
VIP_RESERVATION_ROLES = (
    models.StaffRole.admin,
    models.StaffRole.manager,
    models.StaffRole.receptionist,  # host/floor manager
)
WAITLIST_MANAGEMENT_ROLES = (
    models.StaffRole.admin,
    models.StaffRole.manager,
    models.StaffRole.waiter,
    models.StaffRole.receptionist,
)


# ── response schemas (local, specific to this module) ─────────────────────────

class WaitlistPositionResponse(BaseModel):
    position: int
    entry: schemas.WaitlistEntryResponse


class WaitlistQueueItem(BaseModel):
    position: int
    score: float
    entry: schemas.WaitlistEntryResponse


class PublicWaitlistStatus(BaseModel):
    queue_size: int


# ── helpers ────────────────────────────────────────────────────────────────────

def _ordered_waitlist(db: Session):
    """Order persisted active entries using the score-equivalent SQL expression."""
    score_order = (
        models.WaitlistEntry.priority_tier * 1000
        + extract("epoch", models.WaitlistEntry.joined_at)
        - models.WaitlistEntry.party_size * 5
    )
    return (
        db.query(models.WaitlistEntry, score_order.label("score"))
        .filter(models.WaitlistEntry.status == models.WaitlistStatus.waiting)
        .order_by(score_order.asc(), models.WaitlistEntry.id.asc())
        .all()
    )


def _tier_to_type(priority_tier: int) -> str:
    if priority_tier == 1:
        return "vip"
    if priority_tier == 2:
        return "reservation"
    return "walk_in"


def _award_loyalty_points(customer_id: Optional[int], entry_type: str, db: Session) -> None:
    """Award loyalty points to a customer account based on entry type."""
    if not customer_id:
        return
    customer = db.query(models.Customer).filter(models.Customer.id == customer_id).first()
    if not customer:
        return
    if entry_type == "vip":
        customer.loyalty_points += 20
    elif entry_type == "reservation":
        customer.loyalty_points += 10
    # walk_in gets no points


# ── routes ─────────────────────────────────────────────────────────────────────

@router.post("/join", response_model=WaitlistPositionResponse, status_code=201)
def join_waitlist(payload: schemas.WaitlistEntryCreate, db: Session = Depends(get_db)):
    """
    Public endpoint — walk-in guests (priority_tier=3) can join without auth.
    VIP (tier=1) and Reservation (tier=2) entries require staff auth; use /join/staff instead.
    Walk-in entries cannot carry a customer_id through this public route (security).
    """
    # Only walk-in allowed on unauthenticated public endpoint
    if payload.priority_tier != 3:
        raise HTTPException(
            status_code=403,
            detail="VIP and Reservation entries must be added by staff via /waitlist/staff-join"
        )

    entry = models.WaitlistEntry(
        guest_name=payload.guest_name,
        party_size=payload.party_size,
        priority_tier=3,
        entry_type="walk_in",
        joined_at=datetime.now(timezone.utc),
        customer_id=None,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)

    position = next(i for i, (queued_entry, _) in enumerate(_ordered_waitlist(db), 1) if queued_entry.id == entry.id)
    return WaitlistPositionResponse(
        position=position,
        entry=schemas.WaitlistEntryResponse.model_validate(entry),
    )


@router.post("/staff-join", response_model=WaitlistPositionResponse, status_code=201)
def staff_join_waitlist(
    payload: schemas.WaitlistEntryCreate,
    db: Session = Depends(get_db),
    staff: models.Staff = Depends(require_roles(*VIP_RESERVATION_ROLES)),
):
    """
    Staff-only endpoint for adding VIP or Reservation guests.
    Only Admin, Manager, and Host/Receptionist can use this.
    Awards loyalty points (+20 VIP, +10 Reservation) to linked customer accounts.
    """
    entry_type = _tier_to_type(payload.priority_tier)

    entry = models.WaitlistEntry(
        guest_name=payload.guest_name,
        party_size=payload.party_size,
        priority_tier=payload.priority_tier,
        entry_type=entry_type,
        joined_at=datetime.now(timezone.utc),
        customer_id=payload.customer_id,
    )
    db.add(entry)

    # Award loyalty points to account-holding customers
    _award_loyalty_points(payload.customer_id, entry_type, db)

    db.commit()
    db.refresh(entry)

    position = next(i for i, (queued_entry, _) in enumerate(_ordered_waitlist(db), 1) if queued_entry.id == entry.id)
    return WaitlistPositionResponse(
        position=position,
        entry=schemas.WaitlistEntryResponse.model_validate(entry),
    )


@router.get("/status", response_model=PublicWaitlistStatus)
def get_public_waitlist_status(db: Session = Depends(get_db)):
    """Return aggregate queue information without exposing guest details."""
    count = db.query(models.WaitlistEntry).filter(
        models.WaitlistEntry.status == models.WaitlistStatus.waiting
    ).count()
    return PublicWaitlistStatus(queue_size=count)


@router.get("/", response_model=List[WaitlistQueueItem])
def get_waitlist(
    db: Session = Depends(get_db),
    _: models.Staff = Depends(get_current_staff),
):
    """Return detailed waitlist data to authenticated staff only."""
    ordered_entries = _ordered_waitlist(db)
    now_epoch = datetime.now(timezone.utc).timestamp()
    return [
        WaitlistQueueItem(
            position=i + 1,
            score=round(float(score) - now_epoch, 2),
            entry=schemas.WaitlistEntryResponse.model_validate(entry),
        )
        for i, (entry, score) in enumerate(ordered_entries)
    ]


@router.post("/{entry_id}/remove", response_model=schemas.WaitlistEntryResponse)
def remove_waitlist_entry(
    entry_id: int,
    db: Session = Depends(get_db),
    _: models.Staff = Depends(require_roles(*WAITLIST_MANAGEMENT_ROLES)),
):
    entry = db.query(models.WaitlistEntry).filter(
        models.WaitlistEntry.id == entry_id
    ).with_for_update().populate_existing().first()
    if not entry:
        raise HTTPException(status_code=404, detail="Waitlist entry not found")
    if entry.status == models.WaitlistStatus.seated:
        raise HTTPException(status_code=409, detail="A seated guest cannot be removed from the waitlist")
    if entry.status == models.WaitlistStatus.waiting:
        entry.status = models.WaitlistStatus.removed
        db.commit()
        db.refresh(entry)
    return entry


@router.post("/{entry_id}/seat", response_model=schemas.WaitlistEntryResponse)
def seat_waitlist_entry(
    entry_id: int,
    payload: schemas.WaitlistSeatRequest,
    db: Session = Depends(get_db),
    _: models.Staff = Depends(require_roles(*WAITLIST_MANAGEMENT_ROLES)),
):
    entry_snapshot = db.query(models.WaitlistEntry).filter(
        models.WaitlistEntry.id == entry_id
    ).first()
    if not entry_snapshot:
        raise HTTPException(status_code=404, detail="Waitlist entry not found")

    # Use the same table -> reservation -> waitlist lock order as reservation updates.
    table = db.query(models.Table).filter(
        models.Table.id == payload.table_id
    ).with_for_update().first()
    if not table:
        raise HTTPException(status_code=404, detail="Table not found")
    if table.status != models.TableStatus.available:
        raise HTTPException(status_code=409, detail="Table is not available")
    if table.capacity < entry_snapshot.party_size:
        raise HTTPException(status_code=422, detail="Party size exceeds table capacity")

    reservation = None
    if entry_snapshot.reservation_id is not None:
        reservation = db.query(models.Reservation).filter(
            models.Reservation.id == entry_snapshot.reservation_id
        ).with_for_update().populate_existing().first()
        if not reservation:
            raise HTTPException(status_code=409, detail="Linked reservation no longer exists")
        if reservation.status not in ACTIVE_RESERVATION_STATUSES:
            raise HTTPException(status_code=409, detail="Linked reservation is no longer active")
        if reservation.table_id not in (None, table.id):
            raise HTTPException(status_code=409, detail="Reservation is assigned to a different table")
        if reservation.start_time > datetime.now(timezone.utc).replace(tzinfo=None):
            raise HTTPException(status_code=409, detail="Reservation seating time has not started")
        if reservation.party_size > table.capacity:
            raise HTTPException(status_code=422, detail="Party size exceeds table capacity")
        interval_start = reservation.start_time
        interval_end = interval_start + timedelta(minutes=reservation.duration_minutes)
        exclude_reservation_id = reservation.id
    else:
        interval_start = datetime.now(timezone.utc).replace(tzinfo=None)
        interval_end = interval_start + timedelta(minutes=60)
        exclude_reservation_id = None

    ensure_table_interval_available(
        db,
        table.id,
        interval_start,
        interval_end,
        exclude_reservation_id=exclude_reservation_id,
    )

    entry = db.query(models.WaitlistEntry).filter(
        models.WaitlistEntry.id == entry_id
    ).with_for_update().populate_existing().first()
    if not entry:
        raise HTTPException(status_code=404, detail="Waitlist entry not found")
    if entry.status != models.WaitlistStatus.waiting:
        raise HTTPException(status_code=409, detail=f"Waitlist entry is already {entry.status.value}")

    if reservation:
        reservation.table_id = table.id
        reservation.status = models.ReservationStatus.confirmed
    table.status = models.TableStatus.occupied
    table.current_customer_id = entry.customer_id
    table.current_guest_name = entry.guest_name
    table.current_party_size = entry.party_size
    entry.status = models.WaitlistStatus.seated
    entry.seated_table_id = table.id
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Seating conflicts with an existing reservation") from exc
    db.refresh(entry)
    return entry
