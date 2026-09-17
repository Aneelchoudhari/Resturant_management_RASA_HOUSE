from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app import models, schemas

router = APIRouter(prefix="/reservations", tags=["reservations"])


@router.post("/", response_model=schemas.ReservationResponse, status_code=201)
def create_reservation(payload: schemas.ReservationCreate, db: Session = Depends(get_db)):
    reservation = models.Reservation(
        guest_name=payload.guest_name,
        party_size=payload.party_size,
        start_time=payload.start_time,
        duration_minutes=payload.duration_minutes,
        table_id=payload.table_id,
        status=models.ReservationStatus.pending,
    )
    db.add(reservation)
    db.commit()
    db.refresh(reservation)
    return reservation


@router.get("/", response_model=List[schemas.ReservationResponse])
def list_reservations(db: Session = Depends(get_db)):
    return db.query(models.Reservation).all()
