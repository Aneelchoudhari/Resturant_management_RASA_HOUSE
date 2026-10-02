from datetime import datetime, timedelta

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app import models


ACTIVE_RESERVATION_STATUSES = (models.ReservationStatus.pending, models.ReservationStatus.confirmed)


def ensure_table_interval_available(
    db: Session,
    table_id: int,
    start_time: datetime,
    end_time: datetime,
    exclude_reservation_id: int | None = None,
) -> None:
    query = db.query(models.Reservation).filter(
        models.Reservation.table_id == table_id,
        models.Reservation.status.in_(ACTIVE_RESERVATION_STATUSES),
    )
    if exclude_reservation_id is not None:
        query = query.filter(models.Reservation.id != exclude_reservation_id)
    for existing in query.with_for_update().all():
        existing_end = existing.start_time + timedelta(minutes=existing.duration_minutes)
        if start_time < existing_end and end_time > existing.start_time:
            raise HTTPException(status_code=409, detail="Table already has an overlapping reservation")