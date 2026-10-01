import os
from datetime import datetime, timezone

os.environ["DATABASE_URL"] = "sqlite:///./test_restaurant.db"

from fastapi.testclient import TestClient

from app import models
from app.database import Base, SessionLocal, engine
from app.main import app


def test_get_order_by_id_returns_order():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        db.query(models.Order).delete()
        db.query(models.Table).delete()
        db.commit()

        table = models.Table(number=777, capacity=6, status=models.TableStatus.available)
        db.add(table)
        db.commit()
        db.refresh(table)

        order = models.Order(
            table_id=table.id,
            status=models.OrderStatus.pending,
            created_at=datetime.now(timezone.utc),
        )
        db.add(order)
        db.commit()
        db.refresh(order)

        client = TestClient(app)
        response = client.get(f"/orders/{order.id}")

        assert response.status_code == 200
        payload = response.json()
        assert payload["id"] == order.id
        assert payload["table_id"] == table.id
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
