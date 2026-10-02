from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models
from app.auth import create_access_token, hash_password
from app.database import Base, get_db
from app.main import app


def test_get_order_by_id_returns_order():
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=test_engine)
    test_session_factory = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

    def override_get_db():
        db = test_session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    db = test_session_factory()
    try:
        staff_email = "order-detail-test@example.test"
        db.add(
            models.Staff(
                name="Order Detail Test",
                role=models.StaffRole.manager,
                email=staff_email,
                hashed_password=hash_password("test-password"),
                active=1,
            )
        )
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
        token = create_access_token({"sub": staff_email, "role": models.StaffRole.manager.value})
        response = client.get(
            f"/orders/{order.id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["id"] == order.id
        assert payload["table_id"] == table.id
    finally:
        db.close()
        app.dependency_overrides.pop(get_db, None)
        Base.metadata.drop_all(bind=test_engine)
        test_engine.dispose()
