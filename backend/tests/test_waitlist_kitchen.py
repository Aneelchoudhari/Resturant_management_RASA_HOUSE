import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from threading import Barrier
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models
from app.auth import create_access_token, hash_password
from app.database import Base, get_db
from app.main import app


@pytest.fixture
def client():
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=test_engine)
    factory = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

    def override_get_db():
        db = factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client, factory
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=test_engine)
    test_engine.dispose()


def _staff(factory, role=models.StaffRole.receptionist):
    email = f"{role.value}-{uuid4()}@example.test"
    with factory() as db:
        member = models.Staff(
            name=f"{role.value} staff",
            role=role,
            email=email,
            hashed_password=hash_password("test-password"),
            active=1,
        )
        db.add(member)
        db.commit()
        db.refresh(member)
        staff_id = member.id
    token = create_access_token({"sub": email, "role": role.value})
    return {"Authorization": f"Bearer {token}"}, staff_id


def _customer(factory):
    email = f"customer-{uuid4()}@example.test"
    with factory() as db:
        customer = models.Customer(name="Queue Guest", email=email, hashed_password=hash_password("test-password"))
        db.add(customer)
        db.commit()
        db.refresh(customer)
        customer_id = customer.id
    return create_access_token({"sub": email, "role": "customer"}), customer_id


def _table(factory, *, status=models.TableStatus.available, capacity=6):
    with factory() as db:
        table = models.Table(
            number=int(uuid4().int % 2_000_000_000) + 1,
            capacity=capacity,
            status=status,
        )
        db.add(table)
        db.commit()
        db.refresh(table)
        return table.id


def _entry(factory, *, name="Wait Guest", party_size=2, priority=3, customer_id=None, reservation_id=None, joined_at=None):
    with factory() as db:
        entry = models.WaitlistEntry(
            guest_name=name,
            party_size=party_size,
            priority_tier=priority,
            entry_type={1: "vip", 2: "reservation", 3: "walk_in"}[priority],
            customer_id=customer_id,
            reservation_id=reservation_id,
            joined_at=joined_at or datetime.now(timezone.utc),
            status=models.WaitlistStatus.waiting,
        )
        db.add(entry)
        db.commit()
        db.refresh(entry)
        return entry.id


def _menu_item(factory, category="mains", *, stock_quantity=100):
    with factory() as db:
        item = models.MenuItem(
            name=f"Dish {uuid4()}",
            category=category,
            price=12.5,
            available=1,
            stock_quantity=stock_quantity,
        )
        db.add(item)
        db.commit()
        db.refresh(item)
        return item.id


def _create_order(
    client,
    item_id,
    headers,
    *,
    quantity=1,
    route="/orders/",
    key=None,
    order_type="takeaway",
    table_id=None,
):
    payload = {
        "items": [{"menu_item_id": item_id, "quantity": quantity}],
        "order_type": order_type,
    }
    if table_id is not None:
        payload["table_id"] = table_id
    return client.post(
        route,
        json=payload,
        headers={**headers, "Idempotency-Key": key or str(uuid4())},
    )


def test_waitlist_join_and_active_queue_priority(client):
    test_client, factory = client
    start = datetime.now(timezone.utc) - timedelta(minutes=1)
    walkin_id = _entry(factory, name="Walk-in", priority=3, joined_at=start)
    headers, _ = _staff(factory)
    with factory() as db:
        vip = models.WaitlistEntry(
            guest_name="VIP Guest", party_size=2, priority_tier=1, entry_type="vip",
            joined_at=start, status=models.WaitlistStatus.waiting,
        )
        db.add(vip)
        db.commit()
        vip_id = vip.id

    queue = test_client.get("/waitlist/", headers=headers)
    assert queue.status_code == 200
    assert [row["entry"]["id"] for row in queue.json()] == [vip_id, walkin_id]
    assert all(row["entry"]["status"] == "waiting" for row in queue.json())


def test_public_walkin_join_creates_waiting_entry(client):
    test_client, factory = client
    response = test_client.post(
        "/waitlist/join",
        json={"guest_name": "Walk-in Guest", "party_size": 2, "priority_tier": 3},
    )
    assert response.status_code == 201
    assert response.json()["entry"]["status"] == "waiting"
    with factory() as db:
        entry = db.query(models.WaitlistEntry).filter_by(id=response.json()["entry"]["id"]).one()
        assert entry.status == models.WaitlistStatus.waiting


@pytest.mark.parametrize(
    ("guest_name", "party_size"),
    [("   ", 2), ("Walk-in Guest", 0), ("Walk-in Guest", -1), ("Walk-in Guest", 101)],
)
def test_public_waitlist_join_rejects_invalid_name_or_party_size(client, guest_name, party_size):
    test_client, factory = client
    response = test_client.post(
        "/waitlist/join",
        json={"guest_name": guest_name, "party_size": party_size, "priority_tier": 3},
    )

    assert response.status_code == 422
    with factory() as db:
        assert db.query(models.WaitlistEntry).count() == 0


@pytest.mark.parametrize(
    "role",
    [models.StaffRole.admin, models.StaffRole.manager, models.StaffRole.receptionist],
)
def test_staff_customer_lookup_returns_customer_choices_to_allowed_roles(client, role):
    test_client, factory = client
    headers, _ = _staff(factory, role)
    with factory() as db:
        customer = models.Customer(
            name="Lookup Customer",
            email="lookup@example.com",
            hashed_password=hash_password("customer-password"),
        )
        db.add(customer)
        db.commit()
        customer_id = customer.id

    response = test_client.get("/staff/customers", headers=headers)

    assert response.status_code == 200
    assert response.json() == [{
        "id": customer_id,
        "name": "Lookup Customer",
        "email": "lookup@example.com",
        "loyalty_points": 0,
    }]
    assert "hashed_password" not in response.text


def test_staff_customer_lookup_rejects_roles_without_customer_selection_access(client):
    test_client, factory = client
    waiter_headers, _ = _staff(factory, models.StaffRole.waiter)
    customer_token, _ = _customer(factory)

    assert test_client.get("/staff/customers", headers=waiter_headers).status_code == 403
    assert test_client.get(
        "/staff/customers",
        headers={"Authorization": f"Bearer {customer_token}"},
    ).status_code == 401


@pytest.mark.parametrize("priority_tier", [0, 4])
def test_staff_waitlist_join_rejects_invalid_priority_tier(client, priority_tier):
    test_client, factory = client
    headers, _ = _staff(factory, models.StaffRole.manager)
    response = test_client.post(
        "/waitlist/staff-join",
        headers=headers,
        json={"guest_name": "Priority Guest", "party_size": 2, "priority_tier": priority_tier},
    )

    assert response.status_code == 422
    with factory() as db:
        assert db.query(models.WaitlistEntry).count() == 0


def test_remove_waitlist_entry_is_historical_and_idempotent(client):
    test_client, factory = client
    headers, _ = _staff(factory)
    entry_id = _entry(factory)
    removed = test_client.post(f"/waitlist/{entry_id}/remove", headers=headers)
    repeated = test_client.post(f"/waitlist/{entry_id}/remove", headers=headers)
    assert removed.status_code == repeated.status_code == 200
    assert removed.json()["status"] == repeated.json()["status"] == "removed"
    with factory() as db:
        assert db.query(models.WaitlistEntry).filter_by(id=entry_id).count() == 1
    queue = test_client.get("/waitlist/", headers=headers)
    assert queue.json() == []
    table_id = _table(factory)
    seated_after_removal = test_client.post(
        f"/waitlist/{entry_id}/seat",
        json={"table_id": table_id},
        headers=headers,
    )
    assert seated_after_removal.status_code == 409


def test_remove_rejects_seated_entry_and_invalid_id(client):
    test_client, factory = client
    headers, _ = _staff(factory)
    seated_id = _entry(factory)
    with factory() as db:
        db.query(models.WaitlistEntry).filter_by(id=seated_id).one().status = models.WaitlistStatus.seated
        db.commit()
    seated = test_client.post(f"/waitlist/{seated_id}/remove", headers=headers)
    missing = test_client.post("/waitlist/999999/remove", headers=headers)
    assert seated.status_code == 409
    assert missing.status_code == 404


def test_waitlist_seating_persists_table_customer_and_queue_state(client):
    test_client, factory = client
    headers, _ = _staff(factory)
    token, customer_id = _customer(factory)
    table_id = _table(factory, capacity=4)
    entry_id = _entry(factory, name="Seated Guest", party_size=3, customer_id=customer_id)

    response = test_client.post(
        f"/waitlist/{entry_id}/seat",
        json={"table_id": table_id},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "seated"
    assert response.json()["seated_table_id"] == table_id
    with factory() as db:
        entry = db.query(models.WaitlistEntry).filter_by(id=entry_id).one()
        table = db.query(models.Table).filter_by(id=table_id).one()
        assert entry.customer_id == customer_id
        assert entry.status == models.WaitlistStatus.seated
        assert table.status == models.TableStatus.occupied
        assert table.current_customer_id == customer_id
        assert table.current_guest_name == "Seated Guest"
        assert table.current_party_size == 3
    queue = test_client.get("/waitlist/", headers=headers)
    assert queue.json() == []
    assert test_client.get("/waitlist/status").json() == {"queue_size": 0}


def test_seating_rejects_duplicate_missing_unavailable_and_small_table(client):
    test_client, factory = client
    headers, _ = _staff(factory)
    entry_id = _entry(factory, party_size=4)
    available_table = _table(factory, capacity=6)
    success = test_client.post(f"/waitlist/{entry_id}/seat", json={"table_id": available_table}, headers=headers)
    repeated = test_client.post(f"/waitlist/{entry_id}/seat", json={"table_id": available_table}, headers=headers)
    missing_entry = test_client.post("/waitlist/99999/seat", json={"table_id": available_table}, headers=headers)
    occupied = _table(factory, status=models.TableStatus.occupied)
    another = _entry(factory, party_size=2)
    unavailable = test_client.post(f"/waitlist/{another}/seat", json={"table_id": occupied}, headers=headers)
    small = _table(factory, capacity=1)
    too_small = test_client.post(f"/waitlist/{another}/seat", json={"table_id": small}, headers=headers)
    assert success.status_code == 200
    assert repeated.status_code == 409
    assert missing_entry.status_code == 404
    assert unavailable.status_code == 409
    assert too_small.status_code == 422


def test_seating_reservation_waitlist_conflict_and_persistence(client):
    test_client, factory = client
    headers, _ = _staff(factory)
    table_id = _table(factory, capacity=6)
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    with factory() as db:
        reservation = models.Reservation(
            guest_name="Booked Guest",
            party_size=3,
            start_time=now - timedelta(minutes=5),
            duration_minutes=60,
            status=models.ReservationStatus.pending,
        )
        db.add(reservation)
        db.flush()
        entry = models.WaitlistEntry(
            guest_name="Booked Guest", party_size=3, priority_tier=2,
            entry_type="reservation", reservation_id=reservation.id,
            joined_at=now, status=models.WaitlistStatus.waiting,
        )
        db.add(entry)
        db.commit()
        entry_id = entry.id
        reservation_id = reservation.id

    response = test_client.post(f"/waitlist/{entry_id}/seat", json={"table_id": table_id}, headers=headers)
    assert response.status_code == 200
    with factory() as db:
        reservation = db.query(models.Reservation).filter_by(id=reservation_id).one()
        assert reservation.table_id == table_id
        assert reservation.status == models.ReservationStatus.confirmed

    conflict_table = _table(factory, capacity=6)
    conflict_entry = _entry(factory, name="Walk-in Conflict", party_size=2)
    with factory() as db:
        db.add(models.Reservation(
            table_id=conflict_table,
            guest_name="Upcoming Reservation",
            party_size=2,
            start_time=now + timedelta(minutes=15),
            duration_minutes=60,
            status=models.ReservationStatus.confirmed,
        ))
        db.commit()
    conflict = test_client.post(
        f"/waitlist/{conflict_entry}/seat",
        json={"table_id": conflict_table},
        headers=headers,
    )
    assert conflict.status_code == 409
    with factory() as db:
        assert db.query(models.WaitlistEntry).filter_by(id=conflict_entry).one().status == models.WaitlistStatus.waiting
        assert db.query(models.Table).filter_by(id=conflict_table).one().status == models.TableStatus.available


def test_seating_rolls_back_when_waitlist_update_fails(client):
    test_client, factory = client
    headers, _ = _staff(factory)
    entry_id = _entry(factory)
    table_id = _table(factory)

    def fail_waitlist_update(_mapper, _connection, _target):
        raise RuntimeError("simulated waitlist status failure")

    event.listen(models.WaitlistEntry, "before_update", fail_waitlist_update)
    try:
        with pytest.raises(RuntimeError, match="simulated waitlist status failure"):
            test_client.post(f"/waitlist/{entry_id}/seat", json={"table_id": table_id}, headers=headers)
    finally:
        event.remove(models.WaitlistEntry, "before_update", fail_waitlist_update)
    with factory() as db:
        assert db.query(models.WaitlistEntry).filter_by(id=entry_id).one().status == models.WaitlistStatus.waiting
        assert db.query(models.Table).filter_by(id=table_id).one().status == models.TableStatus.available


def test_staff_and_customer_orders_persist_idempotent_station_tickets(client):
    test_client, factory = client
    waiter_headers, _ = _staff(factory, models.StaffRole.waiter)
    chef_headers, _ = _staff(factory, models.StaffRole.chef)
    menu_id = _menu_item(factory, "drinks")
    idempotency_key = str(uuid4())
    first = _create_order(test_client, menu_id, waiter_headers, quantity=2, key=idempotency_key)
    retry = _create_order(test_client, menu_id, waiter_headers, quantity=2, key=idempotency_key)
    assert first.status_code == retry.status_code == 201
    assert first.json()["order"]["id"] == retry.json()["order"]["id"]
    assert len(first.json()["routing"]["drinks"]) == 2
    assert all(ticket["ticket_id"] for ticket in first.json()["routing"]["drinks"])
    with factory() as db:
        assert db.query(models.Order).count() == 1
        assert db.query(models.KitchenTicket).count() == 2
        assert db.query(models.MenuItem).filter_by(id=menu_id).one().stock_quantity == 98

    different_request = _create_order(
        test_client,
        _menu_item(factory, "sides"),
        waiter_headers,
        key=idempotency_key,
    )
    assert different_request.status_code == 409

    customer_token, _ = _customer(factory)
    customer_order = _create_order(
        test_client,
        menu_id,
        {"Authorization": f"Bearer {customer_token}"},
        route="/orders/customer",
    )
    assert customer_order.status_code == 201
    with factory() as db:
        customer_order_row = db.query(models.Order).filter_by(id=customer_order.json()["id"]).one()
        tickets = db.query(models.KitchenTicket).join(models.OrderItem).filter(
            models.OrderItem.order_id == customer_order_row.id
        ).all()
        assert len(tickets) == 1
        assert tickets[0].station == "drinks"


def test_order_rejects_quantity_above_stock_without_persisting(client):
    test_client, factory = client
    waiter_headers, _ = _staff(factory, models.StaffRole.waiter)
    menu_id = _menu_item(factory, stock_quantity=1)

    response = _create_order(test_client, menu_id, waiter_headers, quantity=2)

    assert response.status_code == 409
    with factory() as db:
        assert db.query(models.MenuItem).filter_by(id=menu_id).one().stock_quantity == 1
        assert db.query(models.Order).count() == 0
        assert db.query(models.KitchenTicket).count() == 0


def test_failed_multi_item_order_rolls_back_prior_stock_decrement(client):
    test_client, factory = client
    waiter_headers, _ = _staff(factory, models.StaffRole.waiter)
    first_menu_id = _menu_item(factory, stock_quantity=5)
    second_menu_id = _menu_item(factory, category="sides", stock_quantity=0)

    response = test_client.post(
        "/orders/",
        headers={**waiter_headers, "Idempotency-Key": str(uuid4())},
        json={
            "order_type": "takeaway",
            "items": [
                {"menu_item_id": first_menu_id, "quantity": 2},
                {"menu_item_id": second_menu_id, "quantity": 1},
            ],
        },
    )

    assert response.status_code == 409
    with factory() as db:
        assert db.query(models.MenuItem).filter_by(id=first_menu_id).one().stock_quantity == 5
        assert db.query(models.MenuItem).filter_by(id=second_menu_id).one().stock_quantity == 0
        assert db.query(models.Order).count() == 0
        assert db.query(models.KitchenTicket).count() == 0


def test_unknown_menu_categories_keep_round_robin_unit_distribution(client):
    test_client, factory = client
    waiter_headers, _ = _staff(factory, models.StaffRole.waiter)
    item_id = _menu_item(factory, "mystery")
    response = _create_order(test_client, item_id, waiter_headers, quantity=8)
    assert response.status_code == 201
    stations = {station: len(items) for station, items in response.json()["routing"].items()}
    assert stations == {"grill": 2, "dessert": 2, "drinks": 2, "sides": 2}


def test_dine_in_orders_require_and_persist_a_table(client):
    test_client, factory = client
    waiter_headers, _ = _staff(factory, models.StaffRole.waiter)
    customer_token, _ = _customer(factory)
    customer_headers = {"Authorization": f"Bearer {customer_token}"}
    menu_id = _menu_item(factory)

    staff_without_table = _create_order(
        test_client,
        menu_id,
        waiter_headers,
        order_type="dine_in",
    )
    customer_without_table = _create_order(
        test_client,
        menu_id,
        customer_headers,
        route="/orders/customer",
        order_type="dine_in",
    )
    assert staff_without_table.status_code == customer_without_table.status_code == 422

    table_id = _table(factory)
    valid_dine_in = _create_order(
        test_client,
        menu_id,
        waiter_headers,
        order_type="dine_in",
        table_id=table_id,
    )
    assert valid_dine_in.status_code == 201
    assert valid_dine_in.json()["order"]["table_id"] == table_id
    with factory() as db:
        assert db.query(models.Order).count() == 1


def test_kitchen_ticket_claim_processing_completion_and_restart_persistence(client):
    test_client, factory = client
    waiter_headers, _ = _staff(factory, models.StaffRole.waiter)
    chef_headers, chef_id = _staff(factory, models.StaffRole.chef)
    other_chef_headers, _ = _staff(factory, models.StaffRole.chef)
    menu_id = _menu_item(factory, "mains")
    order = _create_order(test_client, menu_id, waiter_headers)
    ticket_id = order.json()["routing"]["grill"][0]["ticket_id"]

    queue_before = test_client.get("/kitchen/grill", headers=chef_headers)
    assert queue_before.status_code == 200
    assert queue_before.json()["queue_length"] == 1
    claim = test_client.post(f"/kitchen/tickets/{ticket_id}/claim", headers=chef_headers)
    repeated_claim = test_client.post(f"/kitchen/tickets/{ticket_id}/claim", headers=chef_headers)
    other_claim = test_client.post(f"/kitchen/tickets/{ticket_id}/claim", headers=other_chef_headers)
    assert claim.status_code == repeated_claim.status_code == 200
    assert other_claim.status_code == 409
    assert claim.json()["claimed_by_me"] is True

    started = test_client.post(f"/kitchen/tickets/{ticket_id}/start", headers=chef_headers)
    completed = test_client.post(f"/kitchen/tickets/{ticket_id}/complete", headers=chef_headers)
    assert started.status_code == completed.status_code == 200
    assert completed.json()["status"] == "completed"
    assert test_client.get("/kitchen/grill", headers=chef_headers).json()["queue_length"] == 0
    with factory() as db:
        ticket = db.query(models.KitchenTicket).filter_by(id=ticket_id).one()
        parent_order = db.query(models.Order).filter_by(id=ticket.order_item.order_id).one()
        assert ticket.status == models.KitchenTicketStatus.completed
        assert ticket.claimed_by_staff_id == chef_id
        assert parent_order.status == models.OrderStatus.ready

    with TestClient(app) as restarted_client:
        persisted = restarted_client.get("/kitchen/grill", headers=chef_headers)
        assert persisted.status_code == 200
        assert persisted.json()["queue_length"] == 0


def test_kitchen_release_requeues_ticket_and_customer_cannot_manage_kitchen(client):
    test_client, factory = client
    waiter_headers, _ = _staff(factory, models.StaffRole.waiter)
    chef_headers, _ = _staff(factory, models.StaffRole.chef)
    manager_headers, _ = _staff(factory, models.StaffRole.manager)
    customer_token, _ = _customer(factory)
    menu_id = _menu_item(factory, "sides")
    order = _create_order(test_client, menu_id, waiter_headers)
    ticket_id = order.json()["routing"]["sides"][0]["ticket_id"]
    claim = test_client.post(f"/kitchen/tickets/{ticket_id}/claim", headers=chef_headers)
    release = test_client.post(f"/kitchen/tickets/{ticket_id}/release", headers=manager_headers)
    assert claim.status_code == 200
    assert release.status_code == 200
    assert release.json()["status"] == "queued"
    unauthorized = test_client.get("/kitchen/sides", headers={"Authorization": f"Bearer {customer_token}"})
    assert unauthorized.status_code == 401


def test_kitchen_claim_requires_staff_auth_and_invalid_ticket_is_404(client):
    test_client, factory = client
    anonymous = test_client.get("/kitchen/grill")
    chef_headers, _ = _staff(factory, models.StaffRole.chef)
    missing = test_client.post("/kitchen/tickets/999999/claim", headers=chef_headers)
    assert anonymous.status_code == 401
    assert missing.status_code == 404


@pytest.fixture
def postgres_client():
    database_url = os.getenv("STAGE3_TEST_POSTGRES_URL")
    if not database_url:
        pytest.skip("Set STAGE3_TEST_POSTGRES_URL to a disposable PostgreSQL database migrated to head")
    if not database_url.startswith(("postgresql://", "postgresql+psycopg2://")):
        pytest.fail("STAGE3_TEST_POSTGRES_URL must point to PostgreSQL")
    test_engine = create_engine(database_url, pool_size=8, max_overflow=8)
    factory = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

    def override_get_db():
        db = factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client, factory
    app.dependency_overrides.clear()
    test_engine.dispose()


def test_postgres_concurrent_seating_same_waitlist_entry(postgres_client):
    test_client, factory = postgres_client
    headers, _ = _staff(factory)
    entry_id = _entry(factory)
    tables = [_table(factory), _table(factory)]
    barrier = Barrier(2)

    def seat(table_id):
        barrier.wait()
        return test_client.post(f"/waitlist/{entry_id}/seat", json={"table_id": table_id}, headers=headers)

    with ThreadPoolExecutor(max_workers=2) as executor:
        responses = list(executor.map(seat, tables))
    assert sorted(response.status_code for response in responses) == [200, 409]


def test_postgres_concurrent_seating_same_table(postgres_client):
    test_client, factory = postgres_client
    headers, _ = _staff(factory)
    table_id = _table(factory)
    entries = [_entry(factory, name=f"Guest {index}") for index in (1, 2)]
    barrier = Barrier(2)

    def seat(entry_id):
        barrier.wait()
        return test_client.post(f"/waitlist/{entry_id}/seat", json={"table_id": table_id}, headers=headers)

    with ThreadPoolExecutor(max_workers=2) as executor:
        responses = list(executor.map(seat, entries))
    assert sorted(response.status_code for response in responses) == [200, 409]


def test_postgres_concurrent_kitchen_claims_are_serialized(postgres_client):
    test_client, factory = postgres_client
    waiter_headers, _ = _staff(factory, models.StaffRole.waiter)
    chefs = [_staff(factory, models.StaffRole.chef)[0] for _ in range(2)]
    menu_id = _menu_item(factory, "desserts")
    order = _create_order(test_client, menu_id, waiter_headers)
    ticket_id = order.json()["routing"]["dessert"][0]["ticket_id"]
    barrier = Barrier(2)

    def claim(headers):
        barrier.wait()
        return test_client.post(f"/kitchen/tickets/{ticket_id}/claim", headers=headers)

    with ThreadPoolExecutor(max_workers=2) as executor:
        responses = list(executor.map(claim, chefs))
    assert sorted(response.status_code for response in responses) == [200, 409]