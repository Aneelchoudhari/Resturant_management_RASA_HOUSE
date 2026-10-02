from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app import models, schemas
from app.auth import hash_password, verify_password, create_access_token
from app.rate_limit import (
    LOGIN_WINDOW_SECONDS,
    MAX_LOGIN_ATTEMPTS,
    MAX_REGISTRATIONS,
    REGISTRATION_WINDOW_SECONDS,
    limit_auth_attempt,
)

router = APIRouter(prefix="/auth", tags=["auth"])


class TokenResponse(BaseModel):
    access_token: str
    token_type: str


@router.post("/register", status_code=403)
def blocked_staff_registration(request: Request):
    limit_auth_attempt(request, "registration", MAX_REGISTRATIONS, REGISTRATION_WINDOW_SECONDS)
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Staff accounts can only be created by an administrator",
    )


# Staff accounts are provisioned only through POST /staff/, which requires an
# authenticated admin. There is intentionally no public staff registration route.


# ── POST /auth/login ───────────────────────────────────────────────────────────

@router.post("/login", response_model=TokenResponse)
def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """
    Authenticate with email (as username) + password.
    Returns a Bearer JWT on success.
    """
    limit_auth_attempt(request, "login", MAX_LOGIN_ATTEMPTS, LOGIN_WINDOW_SECONDS)
    staff = db.query(models.Staff).filter(models.Staff.email == form_data.username).first()
    if not staff or not staff.active or not verify_password(form_data.password, staff.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token(data={"sub": staff.email, "role": staff.role.value})
    return TokenResponse(access_token=token, token_type="bearer")


@router.post("/customer/register", response_model=schemas.CustomerResponse, status_code=201)
def register_customer(
    payload: schemas.CustomerCreate,
    request: Request,
    db: Session = Depends(get_db),
):
    limit_auth_attempt(request, "registration", MAX_REGISTRATIONS, REGISTRATION_WINDOW_SECONDS)
    existing_customer = db.query(models.Customer).filter(models.Customer.email == payload.email).first()
    existing_staff = db.query(models.Staff).filter(models.Staff.email == payload.email).first()
    if existing_customer or existing_staff:
        raise HTTPException(status_code=400, detail="Email already registered")
    customer = models.Customer(
        name=payload.name,
        email=payload.email,
        hashed_password=hash_password(payload.password),
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


@router.post("/customer/login", response_model=TokenResponse)
def login_customer(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    limit_auth_attempt(request, "login", MAX_LOGIN_ATTEMPTS, LOGIN_WINDOW_SECONDS)
    customer = db.query(models.Customer).filter(models.Customer.email == form_data.username).first()
    if not customer or not verify_password(form_data.password, customer.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect customer email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token(data={"sub": customer.email, "role": "customer"})
    return TokenResponse(access_token=token, token_type="bearer")
