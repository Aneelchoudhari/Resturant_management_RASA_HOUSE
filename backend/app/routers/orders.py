import hashlib
import json
from datetime import datetime, date, time, timedelta, timezone
from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from app.database import get_db
from app import models, schemas
from app.dsa.order_router import STATIONS
from app.auth import get_current_customer, get_current_staff, require_roles
from app.kitchen_queue import ACTIVE_TICKET_STATUSES, enqueue_order_items, order_tickets, station_tickets, ticket_response

router = APIRouter(prefix="/orders", tags=["orders"])
kitchen_router = APIRouter(prefix="/kitchen", tags=["kitchen"])

KITCHEN_ROLES = (
    models.StaffRole.admin,
    models.StaffRole.manager,
    models.StaffRole.chef,
    models.StaffRole.inventory,  # kitchen staff
)

FLOOR_ROLES = (
    models.StaffRole.admin,
    models.StaffRole.manager,
    models.StaffRole.waiter,
    models.StaffRole.receptionist,
)

WAITER_ROLES = (
    models.StaffRole.admin,
    models.StaffRole.manager,
    models.StaffRole.waiter,
)

CASHIER_ROLES = (
    models.StaffRole.admin,
    models.StaffRole.manager,
    models.StaffRole.cashier,
    models.StaffRole.waiter,
)

# ── response schemas ───────────────────────────────────────────────────────────

def _item_name(order_item: models.OrderItem) -> str:
    """Resolve the menu item name for an order item, falling back to id."""
    if order_item.menu_item and order_item.menu_item.name:
        return order_item.menu_item.name
    return f"Item #{order_item.menu_item_id}"


def _serialize_order(order: models.Order) -> schemas.OrderResponse:
    """Serialize an Order model, populating item names."""
    items = [
        schemas.OrderItemResponse(
            id=item.id,
            menu_item_id=item.menu_item_id,
            name=_item_name(item),
            quantity=item.quantity,
            unit_price=item.unit_price,
            special_instructions=item.special_instructions,
        )
        for item in (order.items or [])
    ]
    return schemas.OrderResponse(
        id=order.id,
        table_id=order.table_id,
        status=order.status,
        customer_id=order.customer_id,
        order_type=order.order_type,
        special_instructions=order.special_instructions,
        total_amount=order.total_amount,
        payment_status=order.payment_status,
        payment_method=order.payment_method,
        created_at=order.created_at,
        items=items,
    )


class RoutedItemResponse(BaseModel):
    ticket_id: int
    unit_number: int
    order_id: int
    menu_item_id: int
    name: str
    category: str
    station: str


class OrderRoutingResponse(BaseModel):
    order: schemas.OrderResponse
    routing: dict  # station -> list of RoutedItemResponse


class KitchenTicketResponse(BaseModel):
    ticket_id: int
    order_id: int
    order_item_id: int
    unit_number: int
    menu_item_id: int
    name: str
    category: str
    station: str
    status: models.KitchenTicketStatus
    claimed_by_staff_id: Optional[int]
    claimed_by_me: bool = False


class KitchenQueueResponse(BaseModel):
    station: str
    queue_length: int
    items: List[KitchenTicketResponse]



def _build_order(
    payload: schemas.OrderCreate,
    db: Session,
    customer: Optional[models.Customer] = None,
    idempotency_key: str | None = None,
):
    if payload.order_type == "dine_in" and payload.table_id is None:
        raise HTTPException(status_code=422, detail="Dine-in orders require a table")

    requested_items = payload.items or [
        schemas.OrderItemCreate(menu_item_id=item_id) for item_id in payload.menu_item_ids
    ]
    if not requested_items:
        raise HTTPException(status_code=400, detail="An order must contain at least one item")

    fingerprint_payload = {
        "customer_id": customer.id if customer else None,
        "table_id": payload.table_id,
        "order_type": payload.order_type,
        "special_instructions": payload.special_instructions,
        "items": [
            {
                "menu_item_id": item.menu_item_id,
                "quantity": item.quantity,
                "special_instructions": item.special_instructions,
            }
            for item in requested_items
        ],
    }
    fingerprint = hashlib.sha256(
        json.dumps(fingerprint_payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    existing = db.query(models.Order).filter(
        models.Order.idempotency_key == idempotency_key
    ).first()
    if existing:
        if existing.idempotency_fingerprint != fingerprint:
            raise HTTPException(status_code=409, detail="Idempotency key was already used for another order")
        return existing, order_tickets(db, existing.id)

    order_items = []
    total_amount = 0.0
    for requested in requested_items:
        if requested.quantity < 1:
            raise HTTPException(status_code=400, detail="Item quantity must be at least 1")
        menu_item = db.query(models.MenuItem).filter(
            models.MenuItem.id == requested.menu_item_id
        ).with_for_update().first()
        if not menu_item:
            raise HTTPException(status_code=404, detail=f"MenuItem id={requested.menu_item_id} not found")
        if not menu_item.available:
            raise HTTPException(status_code=409, detail=f"{menu_item.name} is currently unavailable")
        if menu_item.stock_quantity < requested.quantity:
            raise HTTPException(status_code=409, detail=f"{menu_item.name} has insufficient stock")
        menu_item.stock_quantity -= requested.quantity
        total_amount += menu_item.price * requested.quantity
        order_items.append(models.OrderItem(
            menu_item_id=menu_item.id,
            quantity=requested.quantity,
            unit_price=menu_item.price,
            special_instructions=requested.special_instructions,
            menu_item=menu_item,
        ))

    order = models.Order(
        table_id=payload.table_id,
        customer_id=customer.id if customer else None,
        status=models.OrderStatus.placed,
        order_type=payload.order_type,
        special_instructions=payload.special_instructions,
        total_amount=total_amount,
        items=order_items,
        created_at=datetime.now(timezone.utc),
        idempotency_key=idempotency_key,
        idempotency_fingerprint=fingerprint,
    )
    db.add(order)
    try:
        db.flush()
        tickets = enqueue_order_items(db, order.items)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        existing = db.query(models.Order).filter(
            models.Order.idempotency_key == idempotency_key
        ).first()
        if existing and existing.idempotency_fingerprint == fingerprint:
            return existing, order_tickets(db, existing.id)
        raise HTTPException(status_code=409, detail="Order conflicts with an existing request") from exc
    db.refresh(order)
    return order, order_tickets(db, order.id)


# ── POST /orders — staff (waiter) creates an order ────────────────────────────

@router.post("/", response_model=OrderRoutingResponse, status_code=201)
def create_order(
    payload: schemas.OrderCreate,
    db: Session = Depends(get_db),
    _: models.Staff = Depends(require_roles(*WAITER_ROLES)),
    idempotency_key: str = Header(alias="Idempotency-Key", min_length=8, max_length=128),
):
    """
    Waiter/admin creates a dine-in order for a table and routes to kitchen stations.
    """
    order, tickets = _build_order(payload, db, idempotency_key=idempotency_key)

    routing_summary = {station: [] for station in STATIONS}
    for ticket in tickets:
        item = ticket_response(ticket, _.id)
        routing_summary[ticket.station].append(item)

    routing_response = {
        station: [
            RoutedItemResponse(**item)
            for item in items
        ]
        for station, items in routing_summary.items()
    }

    return OrderRoutingResponse(
        order=schemas.OrderResponse.model_validate(order),
        routing=routing_response,
    )


# ── POST /orders/customer — customer places their own order ───────────────────

@router.post("/customer", response_model=schemas.OrderResponse, status_code=201)
def create_customer_order(
    payload: schemas.OrderCreate,
    db: Session = Depends(get_db),
    customer: models.Customer = Depends(get_current_customer),
    idempotency_key: str = Header(alias="Idempotency-Key", min_length=8, max_length=128),
):
    """Customer places an order from their cart."""
    order, _ = _build_order(payload, db, customer, idempotency_key)
    return _serialize_order(order)


# ── GET /orders/mine — customer sees their own orders ─────────────────────────

@router.get("/mine", response_model=List[schemas.OrderResponse])
def get_my_orders(
    db: Session = Depends(get_db),
    customer: models.Customer = Depends(get_current_customer),
):
    return [
        _serialize_order(o)
        for o in (
            db.query(models.Order)
            .filter(models.Order.customer_id == customer.id)
            .order_by(models.Order.created_at.desc())
            .all()
        )
    ]


# ── GET /orders/history ── Staff-only ─────────────────────────────────────────

@router.get("/history", response_model=List[schemas.OrderResponse])
def get_order_history(
    from_date: Optional[date] = Query(default=None, alias="from"),
    to_date: Optional[date] = Query(default=None, alias="to"),
    db: Session = Depends(get_db),
    _: models.Staff = Depends(get_current_staff),  # Auth required — staff only
):
    """Use the indexed order timestamp for date filtering; the database owns history state."""
    if from_date and to_date and from_date > to_date:
        return []
    query = db.query(models.Order)
    if from_date:
        query = query.filter(models.Order.created_at >= datetime.combine(from_date, time.min))
    if to_date and to_date < date.max:
        query = query.filter(models.Order.created_at < datetime.combine(to_date + timedelta(days=1), time.min))
    orders = query.order_by(models.Order.created_at.asc(), models.Order.id.asc()).all()
    return [_serialize_order(order) for order in orders]


# ── GET /orders/active — kitchen/waiter active orders view ────────────────────

@router.get("/active", response_model=List[schemas.OrderResponse])
def get_active_orders(
    db: Session = Depends(get_db),
    _: models.Staff = Depends(get_current_staff),
):
    """Returns all non-completed, non-cancelled orders. Used by waiters and kitchen."""
    active_statuses = [
        models.OrderStatus.placed,
        models.OrderStatus.accepted,
        models.OrderStatus.preparing,
        models.OrderStatus.ready,
        models.OrderStatus.served,
    ]
    orders = (
        db.query(models.Order)
        .filter(models.Order.status.in_(active_statuses))
        .order_by(models.Order.created_at.asc())
        .all()
    )
    return [_serialize_order(o) for o in orders]


# ── GET /orders/{order_id} ─────────────────────────────────────────────────────

@router.get("/{order_id}", response_model=schemas.OrderResponse)
def get_order_by_id(
    order_id: int,
    db: Session = Depends(get_db),
    _: models.Staff = Depends(get_current_staff),  # staff auth required
):
    """Get a single order by ID — requires staff login."""
    order = db.query(models.Order).filter(models.Order.id == order_id).with_for_update().first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return _serialize_order(order)

# ── PUT /orders/{order_id}/status ─────────────────────────────────────────────

@router.put("/{order_id}/status", response_model=schemas.OrderResponse)
def update_order_status(
    order_id: int,
    payload: schemas.OrderStatusUpdate,
    db: Session = Depends(get_db),
    staff: models.Staff = Depends(get_current_staff),
):
    """
    Update an order's status. Roles are enforced per transition:
    - accepted: waiter (acknowledges kitchen has received)
    - preparing: chef, kitchen staff (inventory role)
    - ready: chef, kitchen staff
    - served: waiter
    - completed: cashier, waiter (bill paid/closed)
    - cancelled: waiter, admin, manager
    """
    permissions = {
        models.OrderStatus.accepted: {
            models.StaffRole.admin, models.StaffRole.manager, models.StaffRole.waiter,
            models.StaffRole.chef, models.StaffRole.inventory,  # kitchen can accept orders
        },
        models.OrderStatus.preparing: {models.StaffRole.admin, models.StaffRole.manager, models.StaffRole.chef, models.StaffRole.inventory},
        models.OrderStatus.ready: {models.StaffRole.admin, models.StaffRole.manager, models.StaffRole.chef, models.StaffRole.inventory},
        models.OrderStatus.served: {models.StaffRole.admin, models.StaffRole.manager, models.StaffRole.waiter},
        models.OrderStatus.completed: {models.StaffRole.admin, models.StaffRole.manager, models.StaffRole.cashier, models.StaffRole.waiter},
        models.OrderStatus.cancelled: {models.StaffRole.admin, models.StaffRole.manager, models.StaffRole.waiter},
    }
    allowed_roles = permissions.get(payload.status, {models.StaffRole.admin, models.StaffRole.manager})
    if staff.role not in allowed_roles:
        raise HTTPException(
            status_code=403,
            detail=f"Role '{staff.role.value}' cannot set status to '{payload.status.value}'"
        )
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    order.status = payload.status
    if payload.status in (models.OrderStatus.ready, models.OrderStatus.cancelled):
        ticket_status = (
            models.KitchenTicketStatus.completed
            if payload.status == models.OrderStatus.ready
            else models.KitchenTicketStatus.cancelled
        )
        now = datetime.now(timezone.utc)
        order_tickets_to_close = (
            db.query(models.KitchenTicket)
            .join(models.OrderItem)
            .filter(
                models.OrderItem.order_id == order.id,
                models.KitchenTicket.status.in_(ACTIVE_TICKET_STATUSES),
            )
            .with_for_update()
            .all()
        )
        for ticket in order_tickets_to_close:
            ticket.status = ticket_status
            if ticket_status == models.KitchenTicketStatus.completed:
                ticket.completed_at = now
    db.commit()
    db.refresh(order)
    return order


# ── POST /orders/{order_id}/payment ───────────────────────────────────────────

@router.post("/{order_id}/payment", response_model=schemas.OrderResponse)
def complete_payment(
    order_id: int,
    payload: schemas.PaymentUpdate,
    db: Session = Depends(get_db),
    _: models.Staff = Depends(require_roles(*CASHIER_ROLES)),
):
    """Mark an order as paid — cashier, waiter, admin, manager.
    
    Loyalty discount: for every 100 points a customer has, ₹100 is deducted.
    Used points are consumed from the customer's balance.
    """
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Apply loyalty discount if order is linked to a customer account
    if order.customer_id:
        customer = db.query(models.Customer).filter(models.Customer.id == order.customer_id).first()
        if customer and customer.loyalty_points >= 100:
            discount_units = customer.loyalty_points // 100  # each 100 pts = ₹100
            max_discount = discount_units * 100  # in rupees
            # Discount cannot exceed total bill
            actual_discount = min(max_discount, order.total_amount)
            points_used = int(actual_discount)  # 1 point-unit = ₹1 discount
            # Round down to nearest 100 points used
            points_used = (points_used // 100) * 100
            if points_used > 0:
                order.total_amount = max(0.0, order.total_amount - points_used)
                customer.loyalty_points -= points_used

    order.payment_method = payload.method
    order.payment_status = models.PaymentStatus.paid
    order.status = models.OrderStatus.completed
    db.commit()
    db.refresh(order)
    return order


# ── GET /kitchen/{station} ─────────────────────────────────────────────────────

@kitchen_router.get("/{station}", response_model=KitchenQueueResponse)
def get_kitchen_queue(
    station: str,
    db: Session = Depends(get_db),
    staff: models.Staff = Depends(require_roles(*KITCHEN_ROLES)),
):
    """
    View the current item queue for a kitchen station.
    Valid stations: grill, dessert, drinks, sides.
    Requires chef or kitchen staff (inventory role) authentication.
    """
    if station not in STATIONS:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown station '{station}'. Valid stations: {STATIONS}",
        )
    items = station_tickets(db, station)
    return KitchenQueueResponse(
        station=station,
        queue_length=len(items),
        items=[
            KitchenTicketResponse(**ticket_response(item, staff.id))
            for item in items
        ],
    )


def _locked_kitchen_ticket(db: Session, ticket_id: int) -> tuple[models.KitchenTicket, models.Order]:
    ticket_snapshot = db.query(models.KitchenTicket).filter(
        models.KitchenTicket.id == ticket_id
    ).first()
    if not ticket_snapshot:
        raise HTTPException(status_code=404, detail="Kitchen ticket not found")
    order = db.query(models.Order).filter(
        models.Order.id == ticket_snapshot.order_item.order_id
    ).with_for_update().populate_existing().first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    ticket = db.query(models.KitchenTicket).filter(
        models.KitchenTicket.id == ticket_id
    ).with_for_update().populate_existing().first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Kitchen ticket not found")
    return ticket, order


def _ticket_response(ticket: models.KitchenTicket, staff: models.Staff) -> KitchenTicketResponse:
    return KitchenTicketResponse(**ticket_response(ticket, staff.id))


@kitchen_router.post("/tickets/{ticket_id}/claim", response_model=KitchenTicketResponse)
def claim_kitchen_ticket(
    ticket_id: int,
    db: Session = Depends(get_db),
    staff: models.Staff = Depends(require_roles(*KITCHEN_ROLES)),
):
    ticket, order = _locked_kitchen_ticket(db, ticket_id)
    if ticket.status == models.KitchenTicketStatus.queued:
        ticket.status = models.KitchenTicketStatus.claimed
        ticket.claimed_by_staff_id = staff.id
        ticket.claimed_at = datetime.now(timezone.utc)
        if order.status == models.OrderStatus.placed:
            order.status = models.OrderStatus.accepted
        db.commit()
        db.refresh(ticket)
    elif ticket.status in (models.KitchenTicketStatus.claimed, models.KitchenTicketStatus.processing) and ticket.claimed_by_staff_id == staff.id:
        pass
    else:
        raise HTTPException(status_code=409, detail="Kitchen ticket is already claimed or completed")
    return _ticket_response(ticket, staff)


@kitchen_router.post("/tickets/{ticket_id}/start", response_model=KitchenTicketResponse)
def start_kitchen_ticket(
    ticket_id: int,
    db: Session = Depends(get_db),
    staff: models.Staff = Depends(require_roles(*KITCHEN_ROLES)),
):
    ticket, order = _locked_kitchen_ticket(db, ticket_id)
    if ticket.status == models.KitchenTicketStatus.processing and ticket.claimed_by_staff_id == staff.id:
        return _ticket_response(ticket, staff)
    if ticket.status != models.KitchenTicketStatus.claimed:
        raise HTTPException(status_code=409, detail="Claim the ticket before starting it")
    if ticket.claimed_by_staff_id != staff.id:
        raise HTTPException(status_code=409, detail="Kitchen ticket is claimed by another staff member")
    ticket.status = models.KitchenTicketStatus.processing
    ticket.processing_at = datetime.now(timezone.utc)
    if order.status in (models.OrderStatus.placed, models.OrderStatus.accepted):
        order.status = models.OrderStatus.preparing
    db.commit()
    db.refresh(ticket)
    return _ticket_response(ticket, staff)


@kitchen_router.post("/tickets/{ticket_id}/complete", response_model=KitchenTicketResponse)
def complete_kitchen_ticket(
    ticket_id: int,
    db: Session = Depends(get_db),
    staff: models.Staff = Depends(require_roles(*KITCHEN_ROLES)),
):
    ticket, order = _locked_kitchen_ticket(db, ticket_id)
    if ticket.status == models.KitchenTicketStatus.completed:
        return _ticket_response(ticket, staff)
    if ticket.status != models.KitchenTicketStatus.processing:
        raise HTTPException(status_code=409, detail="Only processing tickets can be completed")
    if ticket.claimed_by_staff_id != staff.id:
        raise HTTPException(status_code=409, detail="Kitchen ticket is claimed by another staff member")
    ticket.status = models.KitchenTicketStatus.completed
    ticket.completed_at = datetime.now(timezone.utc)
    db.flush()
    remaining = (
        db.query(models.KitchenTicket)
        .join(models.OrderItem)
        .filter(
            models.OrderItem.order_id == order.id,
            models.KitchenTicket.status.in_(ACTIVE_TICKET_STATUSES),
        )
        .count()
    )
    if remaining == 0 and order.status not in (models.OrderStatus.cancelled, models.OrderStatus.completed):
        order.status = models.OrderStatus.ready
    db.commit()
    db.refresh(ticket)
    return _ticket_response(ticket, staff)


@kitchen_router.post("/tickets/{ticket_id}/release", response_model=KitchenTicketResponse)
def release_kitchen_ticket(
    ticket_id: int,
    db: Session = Depends(get_db),
    staff: models.Staff = Depends(require_roles(*KITCHEN_ROLES)),
):
    ticket, _ = _locked_kitchen_ticket(db, ticket_id)
    can_release = ticket.claimed_by_staff_id == staff.id or staff.role in (models.StaffRole.admin, models.StaffRole.manager)
    if not can_release:
        raise HTTPException(status_code=403, detail="Only the claimant or a manager can release this ticket")
    if ticket.status not in (models.KitchenTicketStatus.claimed, models.KitchenTicketStatus.processing):
        raise HTTPException(status_code=409, detail="Only claimed or processing tickets can be released")
    ticket.status = models.KitchenTicketStatus.queued
    ticket.claimed_by_staff_id = None
    ticket.claimed_at = None
    ticket.processing_at = None
    db.commit()
    db.refresh(ticket)
    return _ticket_response(ticket, staff)
