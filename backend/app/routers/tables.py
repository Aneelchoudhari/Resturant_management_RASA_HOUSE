from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app import models, schemas
from app.auth import get_current_admin, require_roles

router = APIRouter(prefix="/tables", tags=["tables"])

# Roles allowed to manage tables operationally (but not structural edits)
FLOOR_ROLES = (
    models.StaffRole.admin,
    models.StaffRole.manager,
    models.StaffRole.waiter,
    models.StaffRole.receptionist,  # host
)

# Roles allowed to fully edit table structure
MANAGEMENT_ROLES = (
    models.StaffRole.admin,
    models.StaffRole.manager,
)


@router.get("/", response_model=List[schemas.TableResponse])
def list_tables(db: Session = Depends(get_db)):
    """Public — any client (staff or customer) can see current table statuses."""
    return db.query(models.Table).all()


@router.post("/", response_model=schemas.TableResponse, status_code=201)
def create_table(
    payload: schemas.TableCreate,
    db: Session = Depends(get_db),
    _: models.Staff = Depends(get_current_admin),  # Admin ONLY
):
    existing = db.query(models.Table).filter(models.Table.number == payload.number).first()
    if existing:
        raise HTTPException(status_code=400, detail="Table number already exists")
    table = models.Table(**payload.model_dump())
    db.add(table)
    db.commit()
    db.refresh(table)
    return table


@router.get("/{table_id}", response_model=schemas.TableResponse)
def get_table(table_id: int, db: Session = Depends(get_db)):
    table = db.query(models.Table).filter(models.Table.id == table_id).first()
    if not table:
        raise HTTPException(status_code=404, detail="Table not found")
    return table


@router.put("/{table_id}", response_model=schemas.TableResponse)
def update_table(
    table_id: int,
    payload: schemas.TableUpdate,
    db: Session = Depends(get_db),
    staff: models.Staff = Depends(require_roles(*MANAGEMENT_ROLES)),  # admin/manager full edit
):
    """Full table update (number, capacity, status) — admin and manager only."""
    table = db.query(models.Table).filter(models.Table.id == table_id).first()
    if not table:
        raise HTTPException(status_code=404, detail="Table not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(table, field, value)
    if table.status != models.TableStatus.occupied:
        table.current_customer_id = None
        table.current_guest_name = None
        table.current_party_size = None
    db.commit()
    db.refresh(table)
    return table


@router.patch("/{table_id}/status", response_model=schemas.TableResponse)
def update_table_status(
    table_id: int,
    payload: schemas.TableStatusUpdate,
    db: Session = Depends(get_db),
    _: models.Staff = Depends(require_roles(*FLOOR_ROLES)),  # waiter/host can change status
):
    """Status-only update — waiter and host can mark tables occupied/available/cleaning/reserved."""
    table = db.query(models.Table).filter(models.Table.id == table_id).first()
    if not table:
        raise HTTPException(status_code=404, detail="Table not found")
    table.status = payload.status
    if table.status != models.TableStatus.occupied:
        table.current_customer_id = None
        table.current_guest_name = None
        table.current_party_size = None
    db.commit()
    db.refresh(table)
    return table


@router.delete("/{table_id}", status_code=204)
def delete_table(
    table_id: int,
    db: Session = Depends(get_db),
    _: models.Staff = Depends(get_current_admin),  # Admin ONLY
):
    table = db.query(models.Table).filter(models.Table.id == table_id).first()
    if not table:
        raise HTTPException(status_code=404, detail="Table not found")
    db.delete(table)
    db.commit()
