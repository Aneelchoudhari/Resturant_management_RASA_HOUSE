from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel
from app.models import TableStatus, ReservationStatus, OrderStatus, StaffRole


# ── Table ──────────────────────────────────────────────────────────────────────

class TableCreate(BaseModel):
    number: int
    capacity: int


class TableUpdate(BaseModel):
    number: Optional[int] = None
    capacity: Optional[int] = None
    status: Optional[TableStatus] = None


class TableResponse(BaseModel):
    id: int
    number: int
    capacity: int
    status: TableStatus

    model_config = {"from_attributes": True}


# ── Reservation ────────────────────────────────────────────────────────────────

class ReservationCreate(BaseModel):
    guest_name: str
    party_size: int
    start_time: datetime
    duration_minutes: int = 60
    table_id: Optional[int] = None


class ReservationUpdate(BaseModel):
    status: Optional[ReservationStatus] = None
    table_id: Optional[int] = None


class ReservationResponse(BaseModel):
    id: int
    guest_name: str
    party_size: int
    start_time: datetime
    duration_minutes: int
    status: ReservationStatus
    table_id: Optional[int]

    model_config = {"from_attributes": True}


# ── WaitlistEntry ──────────────────────────────────────────────────────────────

class WaitlistEntryCreate(BaseModel):
    guest_name: str
    party_size: int
    priority_tier: int = 1


class WaitlistEntryResponse(BaseModel):
    id: int
    guest_name: str
    party_size: int
    priority_tier: int
    joined_at: datetime

    model_config = {"from_attributes": True}


# ── MenuItem ───────────────────────────────────────────────────────────────────

class MenuItemCreate(BaseModel):
    name: str
    category: str
    price: float
    tags: Optional[str] = None


class MenuItemUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    price: Optional[float] = None
    tags: Optional[str] = None


class MenuItemResponse(BaseModel):
    id: int
    name: str
    category: str
    price: float
    tags: Optional[str]

    model_config = {"from_attributes": True}


# ── Order ──────────────────────────────────────────────────────────────────────

class OrderCreate(BaseModel):
    table_id: Optional[int] = None
    menu_item_ids: List[int] = []


class OrderUpdate(BaseModel):
    status: Optional[OrderStatus] = None
    table_id: Optional[int] = None


class OrderResponse(BaseModel):
    id: int
    table_id: Optional[int]
    status: OrderStatus
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Staff ──────────────────────────────────────────────────────────────────────

class StaffCreate(BaseModel):
    name: str
    role: StaffRole = StaffRole.staff
    email: str
    password: str


class StaffUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[StaffRole] = None
    email: Optional[str] = None


class StaffResponse(BaseModel):
    id: int
    name: str
    role: StaffRole
    email: str

    model_config = {"from_attributes": True}
