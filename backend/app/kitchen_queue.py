from datetime import datetime, timezone
from typing import Iterable

from sqlalchemy.orm import Session, joinedload

from app import models
from app.dsa.order_router import CATEGORY_MAP, STATIONS


ACTIVE_TICKET_STATUSES = (
    models.KitchenTicketStatus.queued,
    models.KitchenTicketStatus.claimed,
    models.KitchenTicketStatus.processing,
)


def enqueue_order_items(
    db: Session,
    order_items: Iterable[models.OrderItem],
) -> list[models.KitchenTicket]:
    order_items = list(order_items)
    has_unknown_category = any(
        CATEGORY_MAP.get(order_item.menu_item.category.lower()) is None
        for order_item in order_items
    )
    routing_state = None
    if has_unknown_category:
        routing_state = db.query(models.KitchenRoutingState).filter(
            models.KitchenRoutingState.id == 1
        ).with_for_update().populate_existing().first()
        if routing_state is None:
            routing_state = models.KitchenRoutingState(id=1, next_unknown_station=0)
            db.add(routing_state)
            db.flush()

    tickets = []
    for order_item in order_items:
        menu_item = order_item.menu_item
        category = menu_item.category
        mapped_station = CATEGORY_MAP.get(category.lower())
        for unit_number in range(1, order_item.quantity + 1):
            station = mapped_station
            if station is None:
                assert routing_state is not None
                station = STATIONS[routing_state.next_unknown_station % len(STATIONS)]
                routing_state.next_unknown_station += 1
            ticket = models.KitchenTicket(
                order_item=order_item,
                unit_number=unit_number,
                station=station,
                status=models.KitchenTicketStatus.queued,
                created_at=datetime.now(timezone.utc),
            )
            db.add(ticket)
            tickets.append(ticket)
    db.flush()
    return tickets


def order_tickets(db: Session, order_id: int) -> list[models.KitchenTicket]:
    return (
        db.query(models.KitchenTicket)
        .join(models.OrderItem)
        .filter(models.OrderItem.order_id == order_id)
        .options(
            joinedload(models.KitchenTicket.order_item).joinedload(models.OrderItem.menu_item),
            joinedload(models.KitchenTicket.order_item).joinedload(models.OrderItem.order),
        )
        .order_by(models.KitchenTicket.id)
        .all()
    )


def station_tickets(db: Session, station: str) -> list[models.KitchenTicket]:
    return (
        db.query(models.KitchenTicket)
        .filter(
            models.KitchenTicket.station == station,
            models.KitchenTicket.status.in_(ACTIVE_TICKET_STATUSES),
        )
        .options(
            joinedload(models.KitchenTicket.order_item).joinedload(models.OrderItem.menu_item),
            joinedload(models.KitchenTicket.order_item).joinedload(models.OrderItem.order),
        )
        .order_by(models.KitchenTicket.created_at, models.KitchenTicket.id)
        .all()
    )


def ticket_response(ticket: models.KitchenTicket, staff_id: int) -> dict:
    order_item = ticket.order_item
    menu_item = order_item.menu_item
    return {
        "ticket_id": ticket.id,
        "order_id": order_item.order_id,
        "order_item_id": order_item.id,
        "unit_number": ticket.unit_number,
        "menu_item_id": order_item.menu_item_id,
        "name": menu_item.name if menu_item else f"Item #{order_item.menu_item_id}",
        "category": menu_item.category if menu_item else "unknown",
        "station": ticket.station,
        "status": ticket.status,
        "claimed_by_staff_id": ticket.claimed_by_staff_id,
        "claimed_by_me": ticket.claimed_by_staff_id == staff_id,
    }