import enum
from datetime import datetime, timezone
from sqlalchemy import (
    CheckConstraint, Column, Integer, String, Float, DateTime, ForeignKey, Enum, UniqueConstraint, Index, func
)
from sqlalchemy.orm import relationship
from app.database import Base


class TableStatus(str, enum.Enum):
    available = "available"
    occupied = "occupied"
    reserved = "reserved"
    cleaning = "cleaning"


class ReservationStatus(str, enum.Enum):
    pending = "pending"
    confirmed = "confirmed"
    cancelled = "cancelled"
    completed = "completed"


class OrderStatus(str, enum.Enum):
    placed = "placed"
    accepted = "accepted"
    preparing = "preparing"
    ready = "ready"
    served = "served"
    pending = "pending"
    in_progress = "in_progress"
    completed = "completed"
    cancelled = "cancelled"


class PaymentStatus(str, enum.Enum):
    pending = "pending"
    paid = "paid"
    failed = "failed"
    refunded = "refunded"


class PaymentMethod(str, enum.Enum):
    upi = "upi"
    card = "card"
    cash = "cash"


class WaitlistStatus(str, enum.Enum):
    waiting = "waiting"
    seated = "seated"
    removed = "removed"


class KitchenTicketStatus(str, enum.Enum):
    queued = "queued"
    claimed = "claimed"
    processing = "processing"
    completed = "completed"
    cancelled = "cancelled"


class StaffRole(str, enum.Enum):
    staff = "staff"
    admin = "admin"
    manager = "manager"
    waiter = "waiter"
    chef = "chef"
    cashier = "cashier"
    inventory = "inventory"
    receptionist = "receptionist"


class Table(Base):
    __tablename__ = "tables"

    __table_args__ = (
        CheckConstraint("capacity > 0", name="ck_tables_capacity_positive"),
        CheckConstraint(
            "current_party_size IS NULL OR current_party_size > 0",
            name="ck_tables_current_party_size_positive",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    number = Column(Integer, unique=True, nullable=False)
    capacity = Column(Integer, nullable=False)
    status = Column(Enum(TableStatus), default=TableStatus.available, nullable=False)
    current_customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    current_guest_name = Column(String(200), nullable=True)
    current_party_size = Column(Integer, nullable=True)

    reservations = relationship("Reservation", back_populates="table")
    orders = relationship("Order", back_populates="table")


class TableAdjacency(Base):
    __tablename__ = "table_adjacencies"

    __table_args__ = (
        CheckConstraint("table_id_low < table_id_high", name="ck_table_adjacency_canonical_order"),
        UniqueConstraint("table_id_low", "table_id_high", name="uq_table_adjacency_pair"),
    )

    id = Column(Integer, primary_key=True)
    table_id_low = Column(Integer, ForeignKey("tables.id", ondelete="CASCADE"), nullable=False)
    table_id_high = Column(Integer, ForeignKey("tables.id", ondelete="CASCADE"), nullable=False)


Index("ix_table_adjacencies_high", TableAdjacency.table_id_high)


class Reservation(Base):
    __tablename__ = "reservations"

    __table_args__ = (
        CheckConstraint("party_size > 0", name="ck_reservations_party_size_positive"),
        CheckConstraint("duration_minutes > 0", name="ck_reservations_duration_positive"),
    )

    id = Column(Integer, primary_key=True, index=True)
    table_id = Column(Integer, ForeignKey("tables.id"), nullable=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    guest_name = Column(String, nullable=False)
    party_size = Column(Integer, nullable=False)
    start_time = Column(DateTime, nullable=False)
    duration_minutes = Column(Integer, nullable=False, default=60)
    status = Column(Enum(ReservationStatus), default=ReservationStatus.pending, nullable=False)
    idempotency_key = Column(String(128), unique=True, nullable=True)

    table = relationship("Table", back_populates="reservations")
    customer = relationship("Customer", back_populates="reservations")
    waitlist_entry = relationship("WaitlistEntry", back_populates="reservation", uselist=False)


Index(
    "ix_reservations_table_status_start",
    Reservation.table_id,
    Reservation.status,
    Reservation.start_time,
)


class WaitlistEntry(Base):
    __tablename__ = "waitlist_entries"

    id = Column(Integer, primary_key=True, index=True)
    guest_name = Column(String, nullable=False)
    party_size = Column(Integer, nullable=False)
    priority_tier = Column(Integer, default=1, nullable=False)
    joined_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    entry_type = Column(String, default="walk_in", nullable=False)  # vip | reservation | walk_in
    reservation_id = Column(Integer, ForeignKey("reservations.id"), unique=True, nullable=True)
    status = Column(Enum(WaitlistStatus, name="waitliststatus"), default=WaitlistStatus.waiting, server_default="waiting", nullable=False)
    seated_table_id = Column(Integer, ForeignKey("tables.id"), nullable=True)

    customer = relationship("Customer")
    reservation = relationship("Reservation", back_populates="waitlist_entry")


Index(
    "ix_waitlist_entries_status_priority_joined",
    WaitlistEntry.status,
    WaitlistEntry.priority_tier,
    WaitlistEntry.joined_at,
)
Index("ix_waitlist_entries_seated_table_id", WaitlistEntry.seated_table_id)


class MenuItem(Base):
    __tablename__ = "menu_items"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    category = Column(String, nullable=False)
    description = Column(String, nullable=True)
    image_url = Column(String, nullable=True)
    price = Column(Float, nullable=False)
    tags = Column(String, nullable=True)
    available = Column(Integer, default=1, nullable=False)
    stock_quantity = Column(Integer, default=0, nullable=False)
    low_stock_threshold = Column(Integer, default=5, nullable=False)


Index("ix_menu_items_name_lower", func.lower(MenuItem.name))
Index("ix_menu_items_category_lower", func.lower(MenuItem.category))


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    table_id = Column(Integer, ForeignKey("tables.id"), nullable=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    status = Column(Enum(OrderStatus), default=OrderStatus.placed, nullable=False)
    order_type = Column(String, default="dine_in", nullable=False)
    special_instructions = Column(String, nullable=True)
    total_amount = Column(Float, default=0, nullable=False)
    payment_status = Column(Enum(PaymentStatus), default=PaymentStatus.pending, nullable=False)
    payment_method = Column(Enum(PaymentMethod), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    idempotency_key = Column(String(128), unique=True, nullable=True)
    idempotency_fingerprint = Column(String(64), nullable=True)

    table = relationship("Table", back_populates="orders")
    customer = relationship("Customer", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")


Index("ix_orders_created_at_id", Order.created_at, Order.id)


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    menu_item_id = Column(Integer, ForeignKey("menu_items.id"), nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    unit_price = Column(Float, nullable=False)
    special_instructions = Column(String, nullable=True)

    order = relationship("Order", back_populates="items")
    menu_item = relationship("MenuItem")
    kitchen_tickets = relationship("KitchenTicket", back_populates="order_item", cascade="all, delete-orphan")


class KitchenRoutingState(Base):
    __tablename__ = "kitchen_routing_state"

    id = Column(Integer, primary_key=True)
    next_unknown_station = Column(Integer, nullable=False, default=0)


class KitchenTicket(Base):
    __tablename__ = "kitchen_tickets"

    __table_args__ = (
        UniqueConstraint("order_item_id", "unit_number", name="uq_kitchen_ticket_order_item_unit"),
        CheckConstraint("unit_number > 0", name="ck_kitchen_ticket_unit_positive"),
        CheckConstraint("station IN ('grill', 'dessert', 'drinks', 'sides')", name="ck_kitchen_ticket_station_valid"),
    )

    id = Column(Integer, primary_key=True)
    order_item_id = Column(Integer, ForeignKey("order_items.id", ondelete="CASCADE"), nullable=False)
    unit_number = Column(Integer, nullable=False)
    station = Column(String(16), nullable=False)
    status = Column(Enum(KitchenTicketStatus, name="kitchenticketstatus"), default=KitchenTicketStatus.queued, server_default="queued", nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    claimed_by_staff_id = Column(Integer, ForeignKey("staff.id", ondelete="SET NULL"), nullable=True)
    claimed_at = Column(DateTime, nullable=True)
    processing_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    order_item = relationship("OrderItem", back_populates="kitchen_tickets")
    claimed_by = relationship("Staff")


Index(
    "ix_kitchen_tickets_station_status_id",
    KitchenTicket.station,
    KitchenTicket.status,
    KitchenTicket.id,
)
Index("ix_kitchen_tickets_claimed_by", KitchenTicket.claimed_by_staff_id)


class Staff(Base):
    __tablename__ = "staff"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    role = Column(Enum(StaffRole), default=StaffRole.staff, nullable=False)
    email = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    active = Column(Integer, default=1, nullable=False)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    staff_id = Column(Integer, ForeignKey("staff.id"), nullable=True)
    staff_name = Column(String, nullable=False)
    role = Column(String, nullable=False)
    action = Column(String, nullable=False)
    entity_type = Column(String, nullable=True)
    entity_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)


class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    loyalty_points = Column(Integer, default=0, nullable=False)
    reservations = relationship("Reservation", back_populates="customer")
    orders = relationship("Order", back_populates="customer")
