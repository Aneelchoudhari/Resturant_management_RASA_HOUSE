from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app import models, schemas
from app.auth import get_optional_customer, get_optional_staff, get_current_customer, get_current_staff, require_roles
from app.reservation_rules import ACTIVE_RESERVATION_STATUSES, ensure_table_interval_available

router = APIRouter(prefix="/reservations", tags=["reservations"])

RESERVATION_MANAGEMENT_ROLES = (
    models.StaffRole.admin,
    models.StaffRole.manager,
    models.StaffRole.waiter,
    models.StaffRole.receptionist,  # host
)
WAITLIST_PRIORITY_ROLES = (models.StaffRole.admin, models.StaffRole.manager, models.StaffRole.receptionist)


def _ensure_no_conflict(
    db: Session,
    table_id: int,
    start_time: datetime,
    duration_minutes: int,
    exclude_reservation_id: int | None = None,
) -> None:
    ensure_table_interval_available(
        db,
        table_id,
        start_time,
        start_time + timedelta(minutes=duration_minutes),
        exclude_reservation_id=exclude_reservation_id,
    )


def _same_idempotent_request(
    reservation: models.Reservation,
    payload: schemas.ReservationCreate,
    customer: models.Customer | None,
    priority_tier: int,
) -> bool:
    return (
        reservation.guest_name == (customer.name if customer else payload.guest_name)
        and reservation.party_size == payload.party_size
        and reservation.start_time == payload.start_time
        and reservation.duration_minutes == payload.duration_minutes
        and reservation.table_id == payload.table_id
        and reservation.customer_id == (customer.id if customer else None)
        and reservation.waitlist_entry is not None
        and reservation.waitlist_entry.priority_tier == priority_tier
    )


@router.post("/", response_model=schemas.ReservationResponse, status_code=201)
def create_reservation(
    payload: schemas.ReservationCreate,
    db: Session = Depends(get_db),
    customer: models.Customer | None = Depends(get_optional_customer),
    staff: models.Staff | None = Depends(get_optional_staff),
    idempotency_key: str = Header(alias="Idempotency-Key", min_length=8, max_length=128),
):
    """
    Create a reservation. Open to customers (signed-in or guest).
    A signed-in customer gets loyalty points.
    """
    existing_request = db.query(models.Reservation).filter(
        models.Reservation.idempotency_key == idempotency_key
    ).first()
    priority_tier = payload.waitlist_priority_tier if staff else 3
    if existing_request:
        if not _same_idempotent_request(existing_request, payload, customer, priority_tier):
            raise HTTPException(status_code=409, detail="Idempotency key was already used for another reservation")
        return existing_request

    if payload.start_time <= datetime.now(timezone.utc).replace(tzinfo=None):
        raise HTTPException(status_code=422, detail="Reservation time must be in the future")
    if payload.waitlist_priority_tier < 3 and (not staff or staff.role not in WAITLIST_PRIORITY_ROLES):
        raise HTTPException(status_code=403, detail="Only authorized staff can set VIP or reservation priority")

    if payload.table_id is not None:
        table = db.query(models.Table).filter(models.Table.id == payload.table_id).with_for_update().first()
        if not table:
            raise HTTPException(status_code=404, detail="Table not found")
        if table.status != models.TableStatus.available:
            raise HTTPException(status_code=409, detail="Table is not available for reservation")
        if table.capacity < payload.party_size:
            raise HTTPException(status_code=422, detail="Party size exceeds table capacity")
        existing_request = db.query(models.Reservation).filter(
            models.Reservation.idempotency_key == idempotency_key
        ).first()
        if existing_request:
            if not _same_idempotent_request(existing_request, payload, customer, priority_tier):
                raise HTTPException(status_code=409, detail="Idempotency key was already used for another reservation")
            return existing_request
        _ensure_no_conflict(db, table.id, payload.start_time, payload.duration_minutes)

    if customer:
        customer = db.query(models.Customer).filter(models.Customer.id == customer.id).with_for_update().one()

    reservation = models.Reservation(
        guest_name=customer.name if customer else payload.guest_name,
        party_size=payload.party_size,
        start_time=payload.start_time,
        duration_minutes=payload.duration_minutes,
        table_id=payload.table_id,
        status=models.ReservationStatus.pending,
        customer_id=customer.id if customer else None,
        idempotency_key=idempotency_key,
    )
    entry_type = {1: "vip", 2: "reservation", 3: "walk_in"}[priority_tier]
    waitlist_entry = models.WaitlistEntry(
        guest_name=reservation.guest_name,
        party_size=reservation.party_size,
        priority_tier=priority_tier,
        entry_type=entry_type,
        joined_at=datetime.now(timezone.utc),
        customer_id=customer.id if customer else None,
        reservation=reservation,
    )
    if customer:
        customer.loyalty_points += 10
    db.add(reservation)
    db.add(waitlist_entry)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        if idempotency_key:
            existing_request = db.query(models.Reservation).filter(
                models.Reservation.idempotency_key == idempotency_key
            ).first()
            if existing_request and _same_idempotent_request(existing_request, payload, customer, priority_tier):
                return existing_request
        raise HTTPException(status_code=409, detail="Reservation conflicts with an existing booking") from exc
    db.refresh(reservation)
    return reservation


@router.get("/", response_model=List[schemas.ReservationResponse])
def list_reservations(
    db: Session = Depends(get_db),
    _: models.Staff = Depends(get_current_staff),  # Staff auth required — guests cannot view all bookings
):
    """List all reservations — requires staff login to protect guest data."""
    return db.query(models.Reservation).order_by(models.Reservation.start_time.asc()).all()


@router.get("/mine", response_model=List[schemas.ReservationResponse])
def list_my_reservations(
    customer: models.Customer = Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    """Customer sees only their own reservations."""
    return (
        db.query(models.Reservation)
        .filter(models.Reservation.customer_id == customer.id)
        .order_by(models.Reservation.start_time.desc())
        .all()
    )


@router.get("/account", response_model=schemas.CustomerResponse)
def get_customer_account(customer: models.Customer = Depends(get_current_customer)):
    """Return the logged-in customer's profile and loyalty points."""
    return customer


@router.patch("/{reservation_id}/status", response_model=schemas.ReservationResponse)
def update_reservation_status(
    reservation_id: int,
    payload: schemas.ReservationUpdate,
    db: Session = Depends(get_db),
    _: models.Staff = Depends(require_roles(*RESERVATION_MANAGEMENT_ROLES)),
):
    """Update reservation status (confirm, cancel, complete) — host, waiter, admin, manager."""
    reservation = db.query(models.Reservation).filter(models.Reservation.id == reservation_id).first()
    if not reservation:
        raise HTTPException(status_code=404, detail="Reservation not found")
    updates = payload.model_dump(exclude_unset=True)
    target_table_id = updates.get("table_id", reservation.table_id)
    table_ids = sorted({table_id for table_id in (reservation.table_id, target_table_id) if table_id is not None})
    tables = {}
    for table_id in table_ids:
        table = db.query(models.Table).filter(models.Table.id == table_id).with_for_update().first()
        if not table:
            raise HTTPException(status_code=404, detail="Table not found")
        tables[table_id] = table
    reservation = db.query(models.Reservation).filter(
        models.Reservation.id == reservation_id
    ).with_for_update().first()

    start_time = updates.get("start_time", reservation.start_time)
    duration_minutes = updates.get("duration_minutes", reservation.duration_minutes)
    status_value = updates.get("status", reservation.status)
    if status_value in ACTIVE_RESERVATION_STATUSES and start_time <= datetime.now(timezone.utc).replace(tzinfo=None):
        raise HTTPException(status_code=422, detail="Active reservations must be in the future")
    if target_table_id is not None and status_value in ACTIVE_RESERVATION_STATUSES:
        target_table = tables[target_table_id]
        if target_table.status != models.TableStatus.available:
            raise HTTPException(status_code=409, detail="Table is not available for reservation")
        if target_table.capacity < reservation.party_size:
            raise HTTPException(status_code=422, detail="Party size exceeds table capacity")
        _ensure_no_conflict(db, target_table_id, start_time, duration_minutes, reservation.id)

    for field in ("status", "start_time", "duration_minutes"):
        if field in updates:
            setattr(reservation, field, updates[field])
    if "table_id" in updates:
        reservation.table_id = updates["table_id"]
    if reservation.status in (models.ReservationStatus.cancelled, models.ReservationStatus.completed):
        if reservation.waitlist_entry is not None:
            db.delete(reservation.waitlist_entry)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Reservation conflicts with an existing booking") from exc
    db.refresh(reservation)
    return reservation
