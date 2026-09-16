from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel
from app.database import get_db
from app import models, schemas
from app.dsa.order_router import router_instance, STATIONS

router = APIRouter(prefix="/orders", tags=["orders"])
kitchen_router = APIRouter(prefix="/kitchen", tags=["kitchen"])


# ── response schemas ───────────────────────────────────────────────────────────

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


# ── POST /orders ───────────────────────────────────────────────────────────────

@router.post("/", response_model=OrderRoutingResponse, status_code=201)
def create_order(payload: schemas.OrderCreate, db: Session = Depends(get_db)):
    """
    Create an order and route each menu item to the appropriate station queue.
    Items are split by category; unknown categories are distributed round-robin.
    """
    order = models.Order(
        table_id=payload.table_id,
        status=models.OrderStatus.pending,
        created_at=datetime.utcnow(),
    )
    db.add(order)
    db.commit()
    db.refresh(order)

    # Look up menu items to get name + category for routing
    items_to_route = []
    for item_id in payload.menu_item_ids:
        menu_item = db.query(models.MenuItem).filter(models.MenuItem.id == item_id).first()
        if not menu_item:
            raise HTTPException(status_code=404, detail=f"MenuItem id={item_id} not found")
        items_to_route.append({
            "menu_item_id": menu_item.id,
            "name": menu_item.name,
            "category": menu_item.category,
        })

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


# ── GET /kitchen/{station} ─────────────────────────────────────────────────────

@kitchen_router.get("/{station}", response_model=KitchenQueueResponse)
def get_kitchen_queue(station: str):
    """
    View the current item queue for a kitchen station.
    Valid stations: grill, dessert, drinks, sides.
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
