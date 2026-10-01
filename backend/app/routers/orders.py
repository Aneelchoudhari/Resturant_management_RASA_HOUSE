from datetime import datetime, date, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from app.database import get_db
from app import models, schemas
from app.dsa.order_router import router_instance, STATIONS
from app.dsa.order_history import BST
from app.auth import get_current_customer, get_current_staff, require_roles, get_optional_customer

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
    order_id: int
    menu_item_id: int
    name: str
    category: str
    station: str


class OrderRoutingResponse(BaseModel):
    order: schemas.OrderResponse
    routing: dict  # station -> list of RoutedItemResponse


class KitchenQueueResponse(BaseModel):
    station: str
    queue_length: int
    items: List[RoutedItemResponse]



def _build_order(
    payload: schemas.OrderCreate,
    db: Session,
    customer: Optional[models.Customer] = None,
):
    requested_items = payload.items or [
        schemas.OrderItemCreate(menu_item_id=item_id) for item_id in payload.menu_item_ids
    ]
    if not requested_items:
        raise HTTPException(status_code=400, detail="An order must contain at least one item")

    order_items = []
    items_to_route = []
    total_amount = 0.0
    for requested in requested_items:
        if requested.quantity < 1:
            raise HTTPException(status_code=400, detail="Item quantity must be at least 1")
        menu_item = db.query(models.MenuItem).filter(models.MenuItem.id == requested.menu_item_id).first()
        if not menu_item:
            raise HTTPException(status_code=404, detail=f"MenuItem id={requested.menu_item_id} not found")
        if not menu_item.available:
            raise HTTPException(status_code=409, detail=f"{menu_item.name} is currently unavailable")
        total_amount += menu_item.price * requested.quantity
        order_items.append(models.OrderItem(
            menu_item_id=menu_item.id,
            quantity=requested.quantity,
            unit_price=menu_item.price,
            special_instructions=requested.special_instructions,
        ))
        for _ in range(requested.quantity):
            items_to_route.append({
                "menu_item_id": menu_item.id,
                "name": menu_item.name,
                "category": menu_item.category,
            })

    order = models.Order(
        table_id=payload.table_id,
        customer_id=customer.id if customer else None,
        status=models.OrderStatus.placed,
        order_type=payload.order_type,
        special_instructions=payload.special_instructions,
        total_amount=total_amount,
        items=order_items,
        created_at=datetime.now(timezone.utc),
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    return order, items_to_route


# ── POST /orders — staff (waiter) creates an order ────────────────────────────

@router.post("/", response_model=OrderRoutingResponse, status_code=201)
def create_order(
    payload: schemas.OrderCreate,
    db: Session = Depends(get_db),
    _: models.Staff = Depends(require_roles(*WAITER_ROLES)),
):
    """
    Waiter/admin creates a dine-in order for a table and routes to kitchen stations.
    """
    order, items_to_route = _build_order(payload, db)

    routing_summary = router_instance.route_order(order.id, items_to_route)

    routing_response = {
        station: [
            RoutedItemResponse(
                order_id=item.order_id,
                menu_item_id=item.menu_item_id,
                name=item.name,
                category=item.category,
                station=item.station,
            )
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
):
    """Customer places an order from their cart."""
    order, _ = _build_order(payload, db, customer)
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
    """
    Range query over order history using a BST keyed by date.
    Requires staff authentication — customers cannot see all orders.
    """
    orders = db.query(models.Order).all()

    bst = BST()
    for order in orders:
        bst.insert(order.created_at.date(), order)

    if from_date and to_date:
        matched = bst.range_query(from_date, to_date)
    elif from_date:
        matched = bst.range_query(from_date, date.max)
    elif to_date:
        matched = bst.range_query(date.min, to_date)
    else:
        matched = [v for _, v in bst.inorder()]

    return [_serialize_order(o) for o in matched]


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
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
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
    _: models.Staff = Depends(require_roles(*KITCHEN_ROLES)),
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
    items = router_instance.get_queue(station)
    return KitchenQueueResponse(
        station=station,
        queue_length=len(items),
        items=[
            RoutedItemResponse(
                order_id=i.order_id,
                menu_item_id=i.menu_item_id,
                name=i.name,
                category=i.category,
                station=i.station,
            )
            for i in items
        ],
    )
