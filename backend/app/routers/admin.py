from datetime import date, datetime, time, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app import models, schemas
from app.auth import get_current_admin
from app.database import get_db

router = APIRouter(prefix="/admin", tags=["admin"])


def _today_window():
    start = datetime.combine(date.today(), time.min)
    return start, start + timedelta(days=1)


@router.get("/summary")
def get_summary(db: Session = Depends(get_db), _: models.Staff = Depends(get_current_admin)):
    start, end = _today_window()
    reservations_today = db.query(models.Reservation).filter(models.Reservation.start_time >= start, models.Reservation.start_time < end).all()
    orders_today = db.query(models.Order).filter(models.Order.created_at >= start, models.Order.created_at < end).all()
    return {
        "bookings_today": len(reservations_today),
        "upcoming_bookings": db.query(models.Reservation).filter(models.Reservation.start_time >= start, models.Reservation.status != models.ReservationStatus.cancelled).count(),
        "customers_today": len({item.guest_name for item in reservations_today}),
        "revenue_today": sum(item.total_amount for item in orders_today),
        "tables": {status.value: db.query(models.Table).filter(models.Table.status == status).count() for status in models.TableStatus},
        "orders": {status.value: db.query(models.Order).filter(models.Order.status == status).count() for status in models.OrderStatus},
        "menu": {"available": db.query(models.MenuItem).filter(models.MenuItem.available == 1).count(), "unavailable": db.query(models.MenuItem).filter(models.MenuItem.available == 0).count(), "low_stock": db.query(models.MenuItem).filter(models.MenuItem.stock_quantity <= models.MenuItem.low_stock_threshold).count()},
        "active_staff": db.query(models.Staff).filter(models.Staff.active == 1).count(),
    }


@router.get("/customers", response_model=list[schemas.CustomerResponse])
def list_customers(db: Session = Depends(get_db), _: models.Staff = Depends(get_current_admin)):
    return db.query(models.Customer).order_by(models.Customer.name).all()


@router.get("/audit", response_model=list[schemas.AuditLogResponse])
def list_audit_logs(db: Session = Depends(get_db), _: models.Staff = Depends(get_current_admin)):
    return db.query(models.AuditLog).order_by(models.AuditLog.created_at.desc()).limit(100).all()


@router.get("/reports")
def get_reports(db: Session = Depends(get_db), _: models.Staff = Depends(get_current_admin)):
    today = date.today()
    rows = []
    for offset in range(6, -1, -1):
        day = today - timedelta(days=offset)
        start = datetime.combine(day, time.min)
        end = start + timedelta(days=1)
        rows.append({"date": day.isoformat(), "bookings": db.query(models.Reservation).filter(models.Reservation.start_time >= start, models.Reservation.start_time < end).count(), "orders": db.query(models.Order).filter(models.Order.created_at >= start, models.Order.created_at < end).count(), "revenue": db.query(func.coalesce(func.sum(models.Order.total_amount), 0)).filter(models.Order.created_at >= start, models.Order.created_at < end).scalar()})
    return rows


# ── Admin: Table Management ───────────────────────────────────────────────────

@router.post("/tables", response_model=schemas.TableResponse, status_code=201)
def admin_create_table(
    payload: schemas.TableCreate,
    db: Session = Depends(get_db),
    admin: models.Staff = Depends(get_current_admin),
):
    """Admin creates a new table. Table becomes immediately available."""
    existing = db.query(models.Table).filter(models.Table.number == payload.number).first()
    if existing:
        raise HTTPException(status_code=400, detail="Table number already exists")
    table = models.Table(
        number=payload.number,
        capacity=payload.capacity,
        status=models.TableStatus.available,
    )
    db.add(table)
    db.flush()
    db.add(models.AuditLog(
        staff_id=admin.id,
        staff_name=admin.name,
        role=admin.role.value,
        action=f"Created table #{payload.number} (capacity {payload.capacity})",
        entity_type="table",
        entity_id=table.id,
    ))
    db.commit()
    db.refresh(table)
    return table


# ── Admin: Master Table Allocation ───────────────────────────────────────────

@router.post("/tables/allocate", response_model=schemas.AdminTableAllocateResponse)
def admin_allocate_table(
    payload: schemas.AdminTableAllocateRequest,
    db: Session = Depends(get_db),
    admin: models.Staff = Depends(get_current_admin),
):
    """
    Admin master allocation: directly assign any available table to any customer.
    Sets table status to occupied and records an audit log entry.
    """
    table = db.query(models.Table).filter(models.Table.id == payload.table_id).with_for_update().first()
    if not table:
        raise HTTPException(status_code=404, detail="Table not found")
    if table.status != models.TableStatus.available:
        raise HTTPException(status_code=409, detail="Table is not available for allocation")

    # Determine guest name for audit
    guest_name = payload.guest_name
    customer = None
    if payload.customer_id:
        customer = db.query(models.Customer).filter(models.Customer.id == payload.customer_id).first()
        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found")
        guest_name = customer.name

    if not guest_name:
        raise HTTPException(status_code=400, detail="Provide either customer_id or guest_name")

    if payload.party_size > table.capacity:
        raise HTTPException(status_code=422, detail="Party size exceeds table capacity")

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    active_reservations = db.query(models.Reservation).filter(
        models.Reservation.table_id == table.id,
        models.Reservation.status.in_((models.ReservationStatus.pending, models.ReservationStatus.confirmed)),
    ).with_for_update().all()
    if any(
        reservation.start_time + timedelta(minutes=reservation.duration_minutes) > now
        for reservation in active_reservations
    ):
        raise HTTPException(status_code=409, detail="Table is reserved for an active booking")

    # Set table to occupied
    table.status = models.TableStatus.occupied
    table.current_customer_id = customer.id if customer else None
    table.current_guest_name = guest_name
    table.current_party_size = payload.party_size

    db.add(models.AuditLog(
        staff_id=admin.id,
        staff_name=admin.name,
        role=admin.role.value,
        action=f"Admin allocated table #{table.number} to {guest_name}",
        entity_type="table",
        entity_id=table.id,
    ))
    db.commit()
    db.refresh(table)

    return schemas.AdminTableAllocateResponse(
        table_id=table.id,
        table_number=table.number,
        status=table.status,
        customer_id=payload.customer_id,
        guest_name=guest_name,
        party_size=payload.party_size,
    )