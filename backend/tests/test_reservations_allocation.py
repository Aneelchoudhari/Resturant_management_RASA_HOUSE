import os
import time
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
from app.dsa.interval_scheduler import ReservationSlot, TableSlot, allocate
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


def _future_start(hours=2):
    return (datetime.now(timezone.utc) + timedelta(hours=hours)).replace(microsecond=0)


def _create_table(factory, *, status=models.TableStatus.available, capacity=6):
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


def _create_staff(factory, *, role=models.StaffRole.manager):
    email = f"manager-{uuid4()}@example.test"
    with factory() as db:
        staff = models.Staff(
            name="Reservation Manager",
            role=role,
            email=email,
            hashed_password=hash_password("manager-password"),
            active=1,
        )
        db.add(staff)
        db.commit()
    token = create_access_token({"sub": email, "role": role.value})
    return {"Authorization": f"Bearer {token}"}


def _reservation_payload(start_time, **overrides):
    payload = {
        "guest_name": "Test Guest",
        "party_size": 3,
        "start_time": start_time.isoformat(),
        "duration_minutes": 60,
        "waitlist_priority_tier": 3,
    }
    payload.update(overrides)
    return payload


def _create_reservation(client, payload, key=None):
    key = key or str(uuid4())
    return client.post(
        "/reservations/",
        json=payload,
        headers={"Idempotency-Key": key},
    ), key


def test_valid_reservation_creates_waitlist_entry_atomically(client):
    test_client, factory = client
    response, _ = _create_reservation(test_client, _reservation_payload(_future_start()))
    assert response.status_code == 201
    reservation = response.json()
    assert reservation["status"] == "pending"
    with factory() as db:
        entry = db.query(models.WaitlistEntry).filter_by(reservation_id=reservation["id"]).one()
        assert entry.guest_name == "Test Guest"
        assert entry.priority_tier == 3


@pytest.mark.parametrize(
    "overrides",
    [
        {"party_size": 0},
        {"party_size": -1},
        {"duration_minutes": 0},
        {"duration_minutes": -15},
        {"duration_minutes": 1441},
        {"guest_name": "   "},
    ],
)
def test_invalid_reservation_values_are_rejected(client, overrides):
    test_client, _ = client
    response, _ = _create_reservation(test_client, _reservation_payload(_future_start(), **overrides))
    assert response.status_code == 422


def test_reservation_requires_timezone_and_future_time(client):
    test_client, _ = client
    naive = test_client.post(
        "/reservations/",
        json=_reservation_payload(_future_start().replace(tzinfo=None)),
        headers={"Idempotency-Key": str(uuid4())},
    )
    past, _ = _create_reservation(test_client, _reservation_payload(datetime.now(timezone.utc) - timedelta(hours=1)))
    assert naive.status_code == 422
    assert past.status_code == 422


def test_reservation_requires_idempotency_key(client):
    test_client, _ = client
    response = test_client.post("/reservations/", json=_reservation_payload(_future_start()))
    assert response.status_code == 422


def test_invalid_table_reference_and_insufficient_capacity_are_rejected(client):
    test_client, factory = client
    missing = _create_reservation(
        test_client,
        _reservation_payload(_future_start(), table_id=999999),
    )[0]
    small_table_id = _create_table(factory, capacity=2)
    too_large = _create_reservation(
        test_client,
        _reservation_payload(_future_start(), table_id=small_table_id),
    )[0]
    assert missing.status_code == 404
    assert too_large.status_code == 422


def test_overlapping_same_table_reservations_are_rejected(client):
    test_client, factory = client
    table_id = _create_table(factory)
    start = _future_start()
    first, _ = _create_reservation(test_client, _reservation_payload(start, table_id=table_id))
    second, _ = _create_reservation(
        test_client,
        _reservation_payload(start + timedelta(minutes=30), table_id=table_id),
    )
    assert first.status_code == 201
    assert second.status_code == 409


def test_back_to_back_reservations_are_allowed(client):
    test_client, factory = client
    table_id = _create_table(factory)
    start = _future_start()
    first, _ = _create_reservation(test_client, _reservation_payload(start, table_id=table_id))
    second, _ = _create_reservation(
        test_client,
        _reservation_payload(start + timedelta(minutes=60), table_id=table_id),
    )
    assert first.status_code == second.status_code == 201


def test_cancelled_reservation_releases_its_interval(client):
    test_client, factory = client
    table_id = _create_table(factory)
    headers = _create_staff(factory)
    start = _future_start()
    first, _ = _create_reservation(test_client, _reservation_payload(start, table_id=table_id))
    cancelled = test_client.patch(
        f"/reservations/{first.json()['id']}/status",
        json={"status": "cancelled"},
        headers=headers,
    )
    next_reservation, _ = _create_reservation(test_client, _reservation_payload(start, table_id=table_id))
    assert cancelled.status_code == 200
    assert next_reservation.status_code == 201
    with factory() as db:
        assert db.query(models.WaitlistEntry).filter_by(reservation_id=first.json()["id"]).count() == 0


def test_reservation_update_cannot_create_overlap(client):
    test_client, factory = client
    table_id = _create_table(factory)
    headers = _create_staff(factory)
    start = _future_start()
    first, _ = _create_reservation(test_client, _reservation_payload(start))
    second, _ = _create_reservation(test_client, _reservation_payload(start + timedelta(minutes=10)))
    assigned = test_client.patch(
        f"/reservations/{first.json()['id']}/status",
        json={"table_id": table_id},
        headers=headers,
    )
    conflict = test_client.patch(
        f"/reservations/{second.json()['id']}/status",
        json={"table_id": table_id},
        headers=headers,
    )
    assert assigned.status_code == 200
    assert conflict.status_code == 409


@pytest.mark.parametrize(
    "update",
    [
        lambda start: {"start_time": (start + timedelta(minutes=15)).isoformat()},
        lambda start: {"duration_minutes": 75},
    ],
)
def test_reservation_schedule_update_cannot_create_overlap(client, update):
    test_client, factory = client
    table_id = _create_table(factory)
    headers = _create_staff(factory)
    start = _future_start()
    first, _ = _create_reservation(test_client, _reservation_payload(start, table_id=table_id))
    second, _ = _create_reservation(
        test_client,
        _reservation_payload(start + timedelta(minutes=70), table_id=table_id),
    )
    response = test_client.patch(
        f"/reservations/{first.json()['id']}/status",
        json=update(start),
        headers=headers,
    )
    assert second.status_code == 201
    assert response.status_code == 409


def test_idempotent_retry_returns_existing_reservation_without_duplicate_waitlist(client):
    test_client, factory = client
    payload = _reservation_payload(_future_start())
    key = str(uuid4())
    first, _ = _create_reservation(test_client, payload, key)
    retry, _ = _create_reservation(test_client, payload, key)
    assert first.status_code == retry.status_code == 201
    assert first.json()["id"] == retry.json()["id"]
    with factory() as db:
        assert db.query(models.Reservation).count() == 1
        assert db.query(models.WaitlistEntry).count() == 1


def test_customer_reservation_retry_links_waitlist_and_awards_loyalty_once(client):
    test_client, factory = client
    with factory() as db:
        customer = models.Customer(
            name="Account Guest",
            email=f"customer-{uuid4()}@example.test",
            hashed_password=hash_password("customer-password"),
        )
        db.add(customer)
        db.commit()
        customer_id = customer.id
        customer_email = customer.email
    token = create_access_token({"sub": customer_email, "role": "customer"})
    key = str(uuid4())
    headers = {"Authorization": f"Bearer {token}", "Idempotency-Key": key}
    payload = _reservation_payload(_future_start(), guest_name="Submitted Name")

    first = test_client.post("/reservations/", json=payload, headers=headers)
    retry = test_client.post("/reservations/", json=payload, headers=headers)
    assert first.status_code == retry.status_code == 201
    assert first.json()["id"] == retry.json()["id"]
    assert first.json()["guest_name"] == "Account Guest"
    with factory() as db:
        customer = db.query(models.Customer).filter_by(id=customer_id).one()
        entry = db.query(models.WaitlistEntry).filter_by(reservation_id=first.json()["id"]).one()
        assert customer.loyalty_points == 10
        assert entry.customer_id == customer_id
        assert db.query(models.WaitlistEntry).filter_by(reservation_id=first.json()["id"]).count() == 1


def test_idempotency_key_cannot_be_reused_for_different_request(client):
    test_client, _ = client
    key = str(uuid4())
    first, _ = _create_reservation(test_client, _reservation_payload(_future_start()), key)
    different, _ = _create_reservation(
        test_client,
        _reservation_payload(_future_start(hours=5), guest_name="Different Guest"),
        key,
    )
    assert first.status_code == 201
    assert different.status_code == 409


def test_waitlist_insert_failure_rolls_back_reservation(client):
    test_client, factory = client

    def fail_waitlist_insert(_mapper, _connection, _target):
        raise RuntimeError("simulated waitlist insert failure")

    event.listen(models.WaitlistEntry, "before_insert", fail_waitlist_insert)
    try:
        with pytest.raises(RuntimeError, match="simulated waitlist insert failure"):
            _create_reservation(test_client, _reservation_payload(_future_start()))
    finally:
        event.remove(models.WaitlistEntry, "before_insert", fail_waitlist_insert)
    with factory() as db:
        assert db.query(models.Reservation).count() == 0
        assert db.query(models.WaitlistEntry).count() == 0


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (models.TableStatus.occupied, 409),
        (models.TableStatus.reserved, 409),
        (models.TableStatus.cleaning, 409),
    ],
)
def test_admin_cannot_allocate_unavailable_table(client, status, expected):
    test_client, factory = client
    headers = _create_staff(factory, role=models.StaffRole.admin)
    table_id = _create_table(factory, status=status)
    response = test_client.post(
        "/admin/tables/allocate",
        json={"table_id": table_id, "guest_name": "Walk-in", "party_size": 2},
        headers=headers,
    )
    assert response.status_code == expected


def test_admin_allocation_persists_occupant_and_requires_capacity(client):
    test_client, factory = client
    headers = _create_staff(factory, role=models.StaffRole.admin)
    table_id = _create_table(factory, capacity=4)
    oversized = test_client.post(
        "/admin/tables/allocate",
        json={"table_id": table_id, "guest_name": "Large Party", "party_size": 5},
        headers=headers,
    )
    success = test_client.post(
        "/admin/tables/allocate",
        json={"table_id": table_id, "guest_name": "Walk-in", "party_size": 4},
        headers=headers,
    )
    assert oversized.status_code == 422
    assert success.status_code == 200
    assert success.json()["status"] == "occupied"
    repeated = test_client.post(
        "/admin/tables/allocate",
        json={"table_id": table_id, "guest_name": "Second Guest", "party_size": 2},
        headers=headers,
    )
    assert repeated.status_code == 409
    with factory() as db:
        table = db.query(models.Table).filter_by(id=table_id).one()
        assert table.current_guest_name == "Walk-in"
        assert table.current_party_size == 4
        assert table.status == models.TableStatus.occupied


def test_walkin_allocation_preserves_existing_reservations(client):
    test_client, factory = client
    headers = _create_staff(factory, role=models.StaffRole.admin)
    table_id = _create_table(factory)
    reservation, _ = _create_reservation(
        test_client,
        _reservation_payload(_future_start(), table_id=table_id),
    )
    assert reservation.status_code == 201
    response = test_client.post(
        "/admin/tables/allocate",
        json={"table_id": table_id, "guest_name": "Walk-in", "party_size": 2},
        headers=headers,
    )
    assert response.status_code == 409


def test_allocation_preview_respects_preassigned_reservations(client):
    test_client, factory = client
    first_table_id = _create_table(factory)
    second_table_id = _create_table(factory)
    start = _future_start()
    assigned, _ = _create_reservation(
        test_client,
        _reservation_payload(start, table_id=first_table_id),
    )
    candidate, _ = _create_reservation(
        test_client,
        _reservation_payload(start + timedelta(minutes=10)),
    )
    response = test_client.get("/tables/allocate", headers=_create_staff(factory))
    assert response.status_code == 200
    proposals = response.json()["assignments"]
    assert assigned.json()["id"] not in {item["reservation_id"] for item in proposals}
    proposal = next(item for item in proposals if item["reservation_id"] == candidate.json()["id"])
    assert proposal["table_id"] == second_table_id


def test_allocation_response_reports_unassigned_reservation_ids(client):
    test_client, factory = client
    _create_table(factory, capacity=2)
    reservation, _ = _create_reservation(
        test_client,
        _reservation_payload(_future_start(), party_size=8),
    )

    response = test_client.get("/tables/allocate", headers=_create_staff(factory))

    assert response.status_code == 200
    assert response.json()["assignments"] == []
    assert response.json()["unassigned_reservation_ids"] == [reservation.json()["id"]]
    assert "unassigned" not in response.json()


def test_apply_allocation_persists_reservation_table_relationship(client):
    test_client, factory = client
    table_id = _create_table(factory)
    headers = _create_staff(factory)
    reservation, _ = _create_reservation(test_client, _reservation_payload(_future_start()))
    response = test_client.post(
        "/tables/allocate",
        json={"assignments": [{"reservation_id": reservation.json()["id"], "table_id": table_id}]},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()[0]["table_id"] == table_id
    with factory() as db:
        stored = db.query(models.Reservation).filter_by(id=reservation.json()["id"]).one()
        assert stored.table_id == table_id
        assert db.query(models.Table).filter_by(id=table_id).one().status == models.TableStatus.available


def test_apply_allocation_rejects_non_available_tables(client):
    test_client, factory = client
    headers = _create_staff(factory)
    reservation, _ = _create_reservation(test_client, _reservation_payload(_future_start()))
    for status in (models.TableStatus.occupied, models.TableStatus.reserved, models.TableStatus.cleaning):
        table_id = _create_table(factory, status=status)
        response = test_client.post(
            "/tables/allocate",
            json={"assignments": [{"reservation_id": reservation.json()["id"], "table_id": table_id}]},
            headers=headers,
        )
        assert response.status_code == 409


def test_apply_allocation_is_all_or_nothing(client):
    test_client, factory = client
    headers = _create_staff(factory)
    first_table = _create_table(factory)
    occupied_table = _create_table(factory, status=models.TableStatus.occupied)
    first, _ = _create_reservation(test_client, _reservation_payload(_future_start()))
    second, _ = _create_reservation(test_client, _reservation_payload(_future_start(hours=4)))
    response = test_client.post(
        "/tables/allocate",
        json={"assignments": [
            {"reservation_id": first.json()["id"], "table_id": first_table},
            {"reservation_id": second.json()["id"], "table_id": occupied_table},
        ]},
        headers=headers,
    )
    assert response.status_code == 409
    with factory() as db:
        assert db.query(models.Reservation).filter_by(id=first.json()["id"]).one().table_id is None


def test_allocator_uses_existing_interval_blockers():
    start = _future_start().timestamp()
    result = allocate(
        [ReservationSlot(2, start + 600, start + 3600, 2)],
        [TableSlot(10, 4)],
        existing_assignments={10: [(start, start + 1800)]},
    )
    assert result["assignments"] == []
    assert result["unassigned"] == [2]


@pytest.fixture
def postgres_client():
    database_url = os.getenv("STAGE2_TEST_POSTGRES_URL")
    if not database_url:
        pytest.skip("Set STAGE2_TEST_POSTGRES_URL to a disposable migrated PostgreSQL database")
    if not database_url.startswith(("postgresql://", "postgresql+psycopg2://")):
        pytest.fail("STAGE2_TEST_POSTGRES_URL must point to PostgreSQL")

    test_engine = create_engine(database_url, pool_size=5, max_overflow=5)
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


def _seed_postgres_table(factory):
    with factory() as db:
        table = models.Table(
            number=int(uuid4().int % 2_000_000_000) + 1,
            capacity=8,
            status=models.TableStatus.available,
        )
        db.add(table)
        db.commit()
        db.refresh(table)
        return table.id


def test_postgresql_concurrent_reservations_are_serialized(postgres_client):
    client_context, factory = postgres_client
    headers = _create_staff(factory)
    table_id = _seed_postgres_table(factory)
    start = _future_start()
    barrier = Barrier(2)

    def submit(index):
        barrier.wait()
        return client_context.post(
            "/reservations/",
            json=_reservation_payload(start, guest_name=f"Concurrent {index}", table_id=table_id),
            headers={**headers, "Idempotency-Key": str(uuid4())},
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        responses = list(executor.map(submit, (1, 2)))
    assert sorted(response.status_code for response in responses) == [201, 409]


def test_postgresql_concurrent_allocations_are_serialized(postgres_client):
    client_context, factory = postgres_client
    headers = _create_staff(factory)
    table_id = _seed_postgres_table(factory)
    start = _future_start()
    with factory() as db:
        reservations = [
            models.Reservation(
                guest_name=f"Allocation contender {index}",
                party_size=2,
                start_time=start,
                duration_minutes=60,
                status=models.ReservationStatus.pending,
            )
            for index in (1, 2)
        ]
        db.add_all(reservations)
        db.commit()
        reservation_ids = [reservation.id for reservation in reservations]
    barrier = Barrier(2)

    def allocate_reservation(reservation_id):
        barrier.wait()
        return client_context.post(
            "/tables/allocate",
            json={"assignments": [{"reservation_id": reservation_id, "table_id": table_id}]},
            headers=headers,
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        responses = list(executor.map(allocate_reservation, reservation_ids))
    assert sorted(response.status_code for response in responses) == [200, 409]


def test_postgresql_concurrent_admin_seating_is_serialized(postgres_client):
    client_context, factory = postgres_client
    headers = _create_staff(factory, role=models.StaffRole.admin)
    table_id = _seed_postgres_table(factory)
    barrier = Barrier(2)

    def seat_guest(index):
        barrier.wait()
        return client_context.post(
            "/admin/tables/allocate",
            json={"table_id": table_id, "guest_name": f"Walk-in {index}", "party_size": 2},
            headers=headers,
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        responses = list(executor.map(seat_guest, (1, 2)))
    assert sorted(response.status_code for response in responses) == [200, 409]