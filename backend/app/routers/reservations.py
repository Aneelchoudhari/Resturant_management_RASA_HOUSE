from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app import models, schemas
from app.auth import get_optional_customer, get_current_customer, get_current_staff, require_roles

router = APIRouter(prefix="/reservations", tags=["reservations"])

RESERVATION_MANAGEMENT_ROLES = (
    models.StaffRole.admin,
    models.StaffRole.manager,
    models.StaffRole.waiter,
    models.StaffRole.receptionist,  # host
)


@router.post("/", response_model=schemas.ReservationResponse, status_code=201)
def create_reservation(
    payload: schemas.ReservationCreate,
    db: Session = Depends(get_db),
    customer: models.Customer | None = Depends(get_optional_customer),
):
    """
    Create a reservation. Open to customers (signed-in or guest).
    A signed-in customer gets loyalty points.
    """
    reservation = models.Reservation(
        guest_name=customer.name if customer else payload.guest_name,
        party_size=payload.party_size,
        start_time=payload.start_time,
        duration_minutes=payload.duration_minutes,
        table_id=payload.table_id,
        status=models.ReservationStatus.pending,
        customer_id=customer.id if customer else None,
    )
    if customer:
        customer.loyalty_points += 10
    db.add(reservation)
    db.commit()
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
    if payload.status:
        reservation.status = payload.status
    if payload.table_id is not None:
        reservation.table_id = payload.table_id
    db.commit()
    db.refresh(reservation)
    return reservation
