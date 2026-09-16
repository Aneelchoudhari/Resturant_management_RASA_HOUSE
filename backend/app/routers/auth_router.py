from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app import models, schemas
from app.auth import hash_password, verify_password, create_access_token

router = APIRouter(prefix="/auth", tags=["auth"])


class TokenResponse(BaseModel):
    access_token: str
    token_type: str


# ── POST /auth/register ────────────────────────────────────────────────────────

@router.post("/register", response_model=schemas.StaffResponse, status_code=201)
def register(payload: schemas.StaffCreate, db: Session = Depends(get_db)):
    """Create a new staff account. Password is bcrypt-hashed on storage."""
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
    db.commit()
    db.refresh(staff)
    return staff


# ── POST /auth/login ───────────────────────────────────────────────────────────

@router.post("/login", response_model=TokenResponse)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """
    Authenticate with email (as username) + password.
    Returns a Bearer JWT on success.
    """
    staff = db.query(models.Staff).filter(models.Staff.email == form_data.username).first()
    if not staff or not verify_password(form_data.password, staff.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token(data={"sub": staff.email, "role": staff.role.value})
    return TokenResponse(access_token=token, token_type="bearer")
