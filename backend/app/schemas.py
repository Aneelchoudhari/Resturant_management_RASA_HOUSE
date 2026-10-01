from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, EmailStr, field_validator
from app.models import TableStatus, ReservationStatus, OrderStatus, PaymentStatus, PaymentMethod, StaffRole


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
    priority_tier: int = 3  # 1=VIP, 2=Reservation, 3=Walk-in
    customer_id: Optional[int] = None  # link to customer account for loyalty points


class WaitlistEntryResponse(BaseModel):
    id: int
    guest_name: str
    party_size: int
    priority_tier: int
    joined_at: datetime
    customer_id: Optional[int] = None
    entry_type: Optional[str] = "walk_in"  # nullable in DB for pre-migration rows

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
    table_id: int
    customer_id: Optional[int] = None
    guest_name: Optional[str] = None  # used when allocating to walk-in guest


class AdminTableAllocateResponse(BaseModel):
    table_id: int
    table_number: int
    status: TableStatus
    customer_id: Optional[int]
    guest_name: Optional[str]

    model_config = {"from_attributes": True}
