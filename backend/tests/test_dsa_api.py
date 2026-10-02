import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models
from app.auth import create_access_token, hash_password
from app.database import Base, get_db
from app.main import app
import app.routers.graph as graph_router
import app.routers.menu as menu_router
import app.routers.orders as orders_router
import app.routers.waitlist as waitlist_router


@pytest.fixture
def api_client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_get_db():
        db = factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client, factory
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def _staff(factory, role=models.StaffRole.manager):
    email = f"{role.value}-{uuid.uuid4()}@example.test"
    with factory() as db:
        staff = models.Staff(
            name="Index Tester",
            role=role,
            email=email,
            hashed_password=hash_password("test-password"),
            active=1,
        )
        db.add(staff)
        db.commit()
    return {"Authorization": f"Bearer {create_access_token({'sub': email, 'role': role.value})}"}


def _table(factory, number, capacity):
    with factory() as db:
        table = models.Table(number=number, capacity=capacity, status=models.TableStatus.available)
        db.add(table)
        db.commit()
        db.refresh(table)
        return table.id


def test_menu_search_and_category_queries_do_not_construct_request_indexes(api_client, monkeypatch):
    client, factory = api_client
    with factory() as db:
        db.add_all([
            models.MenuItem(name="Burger", category="Mains", price=10, available=1),
            models.MenuItem(name="Butter Chicken", category="mains", price=12, available=1),
            models.MenuItem(name="Brownie", category="Desserts", price=5, available=1),
        ])
        db.commit()

    def forbidden(*_args, **_kwargs):
        raise AssertionError("API must not rebuild Trie/CategoryIndex per request")

    monkeypatch.setattr(menu_router, "Trie", forbidden, raising=False)
    monkeypatch.setattr(menu_router, "CategoryIndex", forbidden, raising=False)
    assert [item["name"] for item in client.get("/menu/search?q=bu").json()] == ["Burger", "Butter Chicken"]
    assert [item["name"] for item in client.get("/menu/category/MAINS").json()] == ["Burger", "Butter Chicken"]
    assert client.get("/menu/search?q=bu%").json() == []


def test_order_history_uses_date_filtered_database_query(api_client, monkeypatch):
    client, factory = api_client
    headers = _staff(factory)
    with factory() as db:
        start = datetime(2026, 1, 1, 10, tzinfo=timezone.utc)
        db.add_all([
            models.Order(
                status=models.OrderStatus.placed,
                created_at=start + timedelta(days=index % 50),
            )
            for index in range(5000)
        ])
        db.commit()

    def forbidden(*_args, **_kwargs):
        raise AssertionError("History API must not rebuild a BST from all orders")

    monkeypatch.setattr(orders_router, "BST", forbidden, raising=False)
    response = client.get("/orders/history?from=2026-01-03&to=2026-01-03", headers=headers)
    assert response.status_code == 200
    assert len(response.json()) == 100


def test_waitlist_queue_uses_database_order_and_stays_private(api_client, monkeypatch):
    client, factory = api_client
    headers = _staff(factory)
    with factory() as db:
        db.add_all([
            models.WaitlistEntry(guest_name="VIP", party_size=2, priority_tier=1, entry_type="vip", joined_at=datetime(2026, 1, 1, tzinfo=timezone.utc)),
            models.WaitlistEntry(guest_name="Walk-in", party_size=2, priority_tier=3, entry_type="walk_in", joined_at=datetime(2026, 1, 1, tzinfo=timezone.utc)),
        ])
        db.commit()

    def forbidden(*_args, **_kwargs):
        raise AssertionError("Waitlist API must not rebuild a heap from all entries")

    monkeypatch.setattr(waitlist_router, "MinHeap", forbidden, raising=False)
    queue = client.get("/waitlist/", headers=headers)
    public = client.get("/waitlist/status")
    assert queue.status_code == 200
    assert [item["entry"]["guest_name"] for item in queue.json()] == ["VIP", "Walk-in"]
    assert public.json() == {"queue_size": 2}
    assert "VIP" not in public.text


def test_table_graph_edges_persist_in_database_and_survive_router_reuse(api_client):
    client, factory = api_client
    headers = _staff(factory)
    first = _table(factory, 11, 4)
    second = _table(factory, 12, 6)
    added = client.post(f"/tables/{first}/adjacent/{second}", headers=headers)
    repeated = client.post(f"/tables/{second}/adjacent/{first}", headers=headers)
    assert added.status_code == repeated.status_code == 201
    with factory() as db:
        assert db.query(models.TableAdjacency).count() == 1

    components = client.get("/tables/combine?party_size=9", headers=headers)
    pair = next(group for group in components.json()["viable_groups"] if len(group["table_ids"]) == 2)
    assert pair["can_seat_party"] is True

    client.delete(f"/tables/{first}/adjacent/{second}", headers=headers)
    with factory() as db:
        assert db.query(models.TableAdjacency).count() == 0
    assert not hasattr(graph_router, "graph_instance")
