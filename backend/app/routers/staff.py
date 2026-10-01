from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app import models, schemas
from app.auth import hash_password, get_current_admin

router = APIRouter(prefix="/staff", tags=["staff"])


@router.get("/", response_model=List[schemas.StaffResponse])
def list_staff(
    db: Session = Depends(get_db),
    _: models.Staff = Depends(get_current_admin),
):
    return db.query(models.Staff).all()


@router.post("/", response_model=schemas.StaffResponse, status_code=201)
def create_staff(
    payload: schemas.StaffCreate,
    db: Session = Depends(get_db),
    _: models.Staff = Depends(get_current_admin),
):
    existing = db.query(models.Staff).filter(models.Staff.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    staff = models.Staff(
        name=payload.name,
        role=payload.role,
        email=payload.email,
        hashed_password=hash_password(payload.password),
    )
    db.add(staff)
    db.flush()
    db.add(models.AuditLog(staff_id=_.id, staff_name=_.name, role=_.role.value, action=f"Created staff account {staff.email}", entity_type="staff", entity_id=staff.id))
    db.commit()
    db.refresh(staff)
    return staff


@router.get("/{staff_id}", response_model=schemas.StaffResponse)
def get_staff(
    staff_id: int,
    db: Session = Depends(get_db),
    _: models.Staff = Depends(get_current_admin),
):
    staff = db.query(models.Staff).filter(models.Staff.id == staff_id).first()
    if not staff:
        raise HTTPException(status_code=404, detail="Staff member not found")
    return staff


@router.put("/{staff_id}", response_model=schemas.StaffResponse)
def update_staff(
    staff_id: int,
    payload: schemas.StaffUpdate,
    db: Session = Depends(get_db),
    _: models.Staff = Depends(get_current_admin),
):
    staff = db.query(models.Staff).filter(models.Staff.id == staff_id).first()
    if not staff:
        raise HTTPException(status_code=404, detail="Staff member not found")
    updates = payload.model_dump(exclude_unset=True)
    if "password" in updates:
        staff.hashed_password = hash_password(updates.pop("password"))
    for field, value in updates.items():
        setattr(staff, field, value)
    db.add(models.AuditLog(staff_id=_.id, staff_name=_.name, role=_.role.value, action=f"Updated staff account {staff.email}", entity_type="staff", entity_id=staff.id))
    db.commit()
    db.refresh(staff)
    return staff


@router.delete("/{staff_id}", status_code=204)
def delete_staff(
    staff_id: int,
    db: Session = Depends(get_db),
    _: models.Staff = Depends(get_current_admin),
):
    staff = db.query(models.Staff).filter(models.Staff.id == staff_id).first()
    if not staff:
        raise HTTPException(status_code=404, detail="Staff member not found")
    db.delete(staff)
    db.add(models.AuditLog(staff_id=_.id, staff_name=_.name, role=_.role.value, action=f"Deleted staff account {staff.email}", entity_type="staff", entity_id=staff.id))
    db.commit()
