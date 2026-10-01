from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from app.database import get_db
from app import models, schemas
from app.auth import get_current_staff, require_roles
from app.dsa.priority_queue import MinHeap, compute_priority_score

router = APIRouter(prefix="/waitlist", tags=["waitlist"])

# Roles that can add VIP and Reservation entries (require staff auth)
VIP_RESERVATION_ROLES = (
    models.StaffRole.admin,
    models.StaffRole.manager,
    models.StaffRole.receptionist,  # host/floor manager
)


# ── response schemas (local, specific to this module) ─────────────────────────

class WaitlistPositionResponse(BaseModel):
    position: int
    entry: schemas.WaitlistEntryResponse


class WaitlistQueueItem(BaseModel):
    position: int
    score: float
    entry: schemas.WaitlistEntryResponse


# ── helpers ────────────────────────────────────────────────────────────────────

def _build_heap(db: Session) -> MinHeap:
    """Load all waitlist entries from DB and build a fresh min-heap."""
    entries = db.query(models.WaitlistEntry).all()
    heap = MinHeap()
    for e in entries:
        score = compute_priority_score(e.priority_tier, e.party_size, e.joined_at)
        heap.push(score, e.id, schemas.WaitlistEntryResponse.model_validate(e))
    return heap


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

    heap = _build_heap(db)
    sorted_entries = heap.to_sorted_list()
    position = next(
        (i + 1 for i, (_, eid, _) in enumerate(sorted_entries) if eid == entry.id),
        heap.size(),
    )
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

    heap = _build_heap(db)
    sorted_entries = heap.to_sorted_list()
    position = next(
        (i + 1 for i, (_, eid, _) in enumerate(sorted_entries) if eid == entry.id),
        heap.size(),
    )
    return WaitlistPositionResponse(
        position=position,
        entry=schemas.WaitlistEntryResponse.model_validate(entry),
    )


@router.get("/", response_model=List[WaitlistQueueItem])
def get_waitlist(db: Session = Depends(get_db)):
    heap = _build_heap(db)
    sorted_entries = heap.to_sorted_list()
    return [
        WaitlistQueueItem(position=i + 1, score=round(score, 2), entry=entry_data)
        for i, (score, _, entry_data) in enumerate(sorted_entries)
    ]
