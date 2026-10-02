from datetime import datetime, timezone
from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field, field_serializer, field_validator, model_validator
from app.models import TableStatus, ReservationStatus, OrderStatus, PaymentStatus, PaymentMethod, StaffRole, WaitlistStatus


# ── Table ──────────────────────────────────────────────────────────────────────

class TableCreate(BaseModel):
    number: int
    capacity: int = Field(gt=0)


class TableUpdate(BaseModel):
    number: Optional[int] = None
    capacity: Optional[int] = Field(default=None, gt=0)
    status: Optional[TableStatus] = None


class TableResponse(BaseModel):
    id: int
    number: int
    capacity: int
    status: TableStatus

    model_config = {"from_attributes": True}


# ── Reservation ────────────────────────────────────────────────────────────────

class ReservationCreate(BaseModel):
    guest_name: str = Field(min_length=1, max_length=200)
    party_size: int = Field(gt=0, le=100)
    start_time: datetime
    duration_minutes: int = Field(default=60, gt=0, le=1440)
    table_id: Optional[int] = Field(default=None, gt=0)
    waitlist_priority_tier: int = Field(default=3, ge=1, le=3)

    @field_validator("guest_name")
    @classmethod
    def guest_name_not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Guest name cannot be blank")
        return value

    @field_validator("start_time")
    @classmethod
    def normalize_start_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Reservation time must include a timezone")
        return value.astimezone(timezone.utc).replace(tzinfo=None)


class CustomerCreate(BaseModel):
    name: str
    email: EmailStr
    password: str

    @field_validator('password')
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError('Password must be at least 6 characters')
        return v


class CustomerResponse(BaseModel):
    id: int
    name: str
    email: str
    loyalty_points: int

    model_config = {"from_attributes": True}


class ReservationUpdate(BaseModel):
    status: Optional[ReservationStatus] = None
    table_id: Optional[int] = Field(default=None, gt=0)
    start_time: Optional[datetime] = None
    duration_minutes: Optional[int] = Field(default=None, gt=0, le=1440)

    @field_validator("start_time")
    @classmethod
    def normalize_start_time(cls, value: Optional[datetime]) -> Optional[datetime]:
        if value is None:
            return value
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Reservation time must include a timezone")
        return value.astimezone(timezone.utc).replace(tzinfo=None)

    @model_validator(mode="after")
    def validate_update_fields(self):
        for field in ("status", "start_time", "duration_minutes"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null")
        if not self.model_fields_set:
            raise ValueError("At least one reservation field must be updated")
        return self


class ReservationResponse(BaseModel):
    id: int
    guest_name: str
    party_size: int
    start_time: datetime
    duration_minutes: int
    status: ReservationStatus
    table_id: Optional[int]

    model_config = {"from_attributes": True}

    @field_serializer("start_time")
    def serialize_start_time(self, value: datetime) -> str:
        return value.replace(tzinfo=timezone.utc).isoformat()


# ── WaitlistEntry ──────────────────────────────────────────────────────────────

class WaitlistEntryCreate(BaseModel):
    guest_name: str = Field(min_length=1, max_length=200)
    party_size: int = Field(gt=0, le=100)
    priority_tier: int = Field(default=3, ge=1, le=3)  # 1=VIP, 2=Reservation, 3=Walk-in
    customer_id: Optional[int] = None  # link to customer account for loyalty points

    @field_validator("guest_name")
    @classmethod
    def guest_name_not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Guest name cannot be blank")
        return value


class WaitlistEntryResponse(BaseModel):
    id: int
    guest_name: str
    party_size: int
    priority_tier: int
    joined_at: datetime
    customer_id: Optional[int] = None
    entry_type: Optional[str] = "walk_in"  # nullable in DB for pre-migration rows
    reservation_id: Optional[int] = None
    status: WaitlistStatus = WaitlistStatus.waiting
    seated_table_id: Optional[int] = None

    model_config = {"from_attributes": True}

    @field_validator("entry_type", mode="before")
    @classmethod
    def default_entry_type(cls, v):
        """Return 'walk_in' if DB returns None (pre-migration rows)."""
        return v if v is not None else "walk_in"


# ── MenuItem ───────────────────────────────────────────────────────────────────

class MenuItemCreate(BaseModel):
    name: str
    category: str
    description: Optional[str] = None
    image_url: Optional[str] = None
    price: float
    tags: Optional[str] = None
    available: bool = True
    stock_quantity: int = 0
    low_stock_threshold: int = 5


class MenuItemUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    price: Optional[float] = None
    tags: Optional[str] = None
    available: Optional[bool] = None
    stock_quantity: Optional[int] = None
    low_stock_threshold: Optional[int] = None


class MenuItemResponse(BaseModel):
    id: int
    name: str
    category: str
    description: Optional[str]
    image_url: Optional[str]
    price: float
    tags: Optional[str]
    available: bool
    stock_quantity: int
    low_stock_threshold: int

    model_config = {"from_attributes": True}


# ── Order ──────────────────────────────────────────────────────────────────────

class OrderCreate(BaseModel):
    table_id: Optional[int] = None
    menu_item_ids: List[int] = []
    items: List["OrderItemCreate"] = []
    order_type: str = "dine_in"
    special_instructions: Optional[str] = None


class OrderItemCreate(BaseModel):
    menu_item_id: int
    quantity: int = 1
    special_instructions: Optional[str] = None


class OrderItemResponse(BaseModel):
    id: int
    menu_item_id: int
    name: Optional[str] = None  # Populated via join/serialization in OrderResponse
    quantity: int
    unit_price: float
    special_instructions: Optional[str]

    model_config = {"from_attributes": True}


OrderCreate.model_rebuild()


class OrderUpdate(BaseModel):
    status: Optional[OrderStatus] = None
    table_id: Optional[int] = None


class OrderStatusUpdate(BaseModel):
    status: OrderStatus


class PaymentUpdate(BaseModel):
    method: PaymentMethod


class OrderResponse(BaseModel):
    id: int
    table_id: Optional[int]
    status: OrderStatus
    customer_id: Optional[int]
    order_type: str
    special_instructions: Optional[str]
    total_amount: float
    payment_status: PaymentStatus
    payment_method: Optional[PaymentMethod]
    created_at: datetime
    items: List[OrderItemResponse] = []

    model_config = {"from_attributes": True}


# ── Staff ──────────────────────────────────────────────────────────────────────

class StaffCreate(BaseModel):
    name: str
    role: StaffRole = StaffRole.waiter
    email: EmailStr
    password: str

    @field_validator('role')
    @classmethod
    def no_admin_self_promotion(cls, v: StaffRole) -> StaffRole:
        # Admin creation via POST /staff/ is blocked; use bootstrap_admin.py
        if v == StaffRole.admin:
            raise ValueError('Cannot create admin accounts via this endpoint. Use the bootstrap script.')
        return v

    @field_validator('password')
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError('Staff password must be at least 8 characters')
        return v


class StaffUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[StaffRole] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    active: Optional[bool] = None

    @field_validator('role')
    @classmethod
    def no_admin_via_update(cls, v: Optional[StaffRole]) -> Optional[StaffRole]:
        # Admin role can only be set via bootstrap_admin.py
        if v == StaffRole.admin:
            raise ValueError('Cannot assign admin role via update. Use the bootstrap script.')
        return v


class StaffResponse(BaseModel):
    id: int
    name: str
    role: StaffRole
    email: str
    active: bool

    model_config = {"from_attributes": True}


class AuditLogResponse(BaseModel):
    id: int
    staff_id: Optional[int]
    staff_name: str
    role: str
    action: str
    entity_type: Optional[str]
    entity_id: Optional[int]
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Kitchen ────────────────────────────────────────────────────────────────────

class KitchenStatusUpdate(BaseModel):
    """Used by chef/kitchen staff to update an order's kitchen status."""
    status: OrderStatus


# ── Waiter Order Addition ──────────────────────────────────────────────────────

class OrderAddItemsRequest(BaseModel):
    """Used by waiters to add items to an existing order or create a new staff order."""
    table_id: Optional[int] = None
    items: List["OrderItemCreate"] = []
    special_instructions: Optional[str] = None
    order_type: str = "dine_in"


# ── Table Status Update ────────────────────────────────────────────────────────

class TableStatusUpdate(BaseModel):
    """For waiter/host to update only the table status, not capacity or number."""
    status: TableStatus


# ── Admin Table Allocation ─────────────────────────────────────────────────────

class AdminTableAllocateRequest(BaseModel):
    """Admin directly allocates a table to a customer (by table_id + customer_id or guest_name)."""
    table_id: int = Field(gt=0)
    customer_id: Optional[int] = Field(default=None, gt=0)
    guest_name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    party_size: int = Field(default=1, gt=0, le=100)


class AdminTableAllocateResponse(BaseModel):
    table_id: int
    table_number: int
    status: TableStatus
    customer_id: Optional[int]
    guest_name: Optional[str]
    party_size: int

    model_config = {"from_attributes": True}


class WaitlistSeatRequest(BaseModel):
    table_id: int = Field(gt=0)


class ReservationTableAllocateRequest(BaseModel):
    reservation_id: int = Field(gt=0)
    table_id: int = Field(gt=0)


class AllocationPlanCommitRequest(BaseModel):
    assignments: List[ReservationTableAllocateRequest] = Field(min_length=1)

    @field_validator("assignments")
    @classmethod
    def unique_reservations(cls, value: List[ReservationTableAllocateRequest]):
        reservation_ids = [assignment.reservation_id for assignment in value]
        if len(reservation_ids) != len(set(reservation_ids)):
            raise ValueError("A reservation may appear only once in an allocation request")
        return value
