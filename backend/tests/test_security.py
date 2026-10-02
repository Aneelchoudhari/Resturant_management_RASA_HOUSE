import runpy
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models
from app.auth import create_access_token, hash_password
from app.database import Base, get_db
from app.main import app
from app.rate_limit import auth_rate_limiter
from app.routers.staff import delete_staff
from app.security_settings import (
    DEVELOPMENT_SECRET_KEY,
    resolve_database_url,
    resolve_secret_key,
)
import app.routers.auth_router as auth_routes


@pytest.fixture
def client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_get_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    auth_rate_limiter.clear()
    with TestClient(app) as test_client:
        yield test_client, session_factory
    app.dependency_overrides.clear()
    auth_rate_limiter.clear()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def _create_staff(session_factory, *, email="staff@example.com", active=1, role=models.StaffRole.waiter):
    with session_factory() as db:
        staff = models.Staff(
            name="Test Staff",
            role=role,
            email=email,
            hashed_password=hash_password("correct-password"),
            active=active,
        )
        db.add(staff)
        db.commit()
        db.refresh(staff)
        return staff.id


def _token(email, role="waiter"):
    return create_access_token(data={"sub": email, "role": role})


def test_public_waitlist_status_contains_no_guest_details(client):
    test_client, session_factory = client
    with session_factory() as db:
        db.add(models.WaitlistEntry(
            guest_name="Private Guest Name",
            party_size=7,
            priority_tier=3,
            joined_at=datetime.now(timezone.utc),
        ))
        db.commit()

    response = test_client.get("/waitlist/status")
    assert response.status_code == 200
    assert response.json() == {"queue_size": 1}
    assert "Private Guest Name" not in response.text
    assert "party_size" not in response.text


def test_anonymous_waitlist_details_require_authentication(client):
    test_client, _ = client
    response = test_client.get("/waitlist/")
    assert response.status_code == 401
    assert "guest_name" not in response.text


def test_staff_can_view_waitlist_details(client):
    test_client, session_factory = client
    _create_staff(session_factory)
    with session_factory() as db:
        db.add(models.WaitlistEntry(
            guest_name="Staff Visible Guest",
            party_size=4,
            priority_tier=3,
            joined_at=datetime.now(timezone.utc),
        ))
        db.commit()

    response = test_client.get(
        "/waitlist/",
        headers={"Authorization": f"Bearer {_token('staff@example.com')}"},
    )
    assert response.status_code == 200
    assert response.json()[0]["entry"]["guest_name"] == "Staff Visible Guest"
    assert response.json()[0]["entry"]["party_size"] == 4


def test_customer_can_only_read_aggregate_waitlist_status(client):
    test_client, session_factory = client
    with session_factory() as db:
        db.add(models.Customer(
            name="Test Customer",
            email="customer@example.com",
            hashed_password=hash_password("customer-password"),
        ))
        db.add(models.WaitlistEntry(
            guest_name="Private Guest Name",
            party_size=5,
            priority_tier=3,
            joined_at=datetime.now(timezone.utc),
        ))
        db.commit()

    token = _token("customer@example.com", "customer")
    detail_response = test_client.get("/waitlist/", headers={"Authorization": f"Bearer {token}"})
    status_response = test_client.get("/waitlist/status", headers={"Authorization": f"Bearer {token}"})
    assert detail_response.status_code == 401
    assert status_response.status_code == 200
    assert status_response.json() == {"queue_size": 1}
    assert "Private Guest Name" not in status_response.text


def test_active_staff_can_login_and_access_protected_route(client):
    test_client, session_factory = client
    _create_staff(session_factory)
    response = test_client.post(
        "/auth/login",
        data={"username": "staff@example.com", "password": "correct-password"},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    protected = test_client.get("/reservations/", headers={"Authorization": f"Bearer {token}"})
    assert protected.status_code == 200


def test_active_admin_can_login_and_access_admin_route(client):
    test_client, session_factory = client
    _create_staff(session_factory, email="admin@example.com", role=models.StaffRole.admin)
    response = test_client.post(
        "/auth/login",
        data={"username": "admin@example.com", "password": "correct-password"},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    protected = test_client.get("/staff/", headers={"Authorization": f"Bearer {token}"})
    assert protected.status_code == 200


def test_customer_token_cannot_use_same_email_staff_privileges(client):
    test_client, session_factory = client
    _create_staff(session_factory, email="admin@example.com", role=models.StaffRole.admin)

    admin_login = test_client.post(
        "/auth/login",
        data={"username": "admin@example.com", "password": "correct-password"},
    )
    assert admin_login.status_code == 200
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}

    customer_registration = test_client.post(
        "/auth/customer/register",
        json={
            "name": "Shared Email Customer",
            "email": "shared@example.com",
            "password": "customer-password",
        },
    )
    assert customer_registration.status_code == 201
    staff_creation = test_client.post(
        "/staff/",
        headers=admin_headers,
        json={
            "name": "Shared Email Manager",
            "role": "manager",
            "email": "shared@example.com",
            "password": "manager-password",
        },
    )
    assert staff_creation.status_code == 201

    customer_login = test_client.post(
        "/auth/customer/login",
        data={"username": "shared@example.com", "password": "customer-password"},
    )
    assert customer_login.status_code == 200
    customer_headers = {"Authorization": f"Bearer {customer_login.json()['access_token']}"}
    menu_payload = {"name": "Protected Probe", "category": "mains", "price": 1}

    rejected = test_client.post("/menu/", headers=customer_headers, json=menu_payload)
    assert rejected.status_code == 401
    with session_factory() as db:
        assert db.query(models.MenuItem).filter_by(name="Protected Probe").count() == 0

    manager_login = test_client.post(
        "/auth/login",
        data={"username": "shared@example.com", "password": "manager-password"},
    )
    assert manager_login.status_code == 200
    manager_headers = {"Authorization": f"Bearer {manager_login.json()['access_token']}"}
    accepted = test_client.post("/menu/", headers=manager_headers, json=menu_payload)
    assert accepted.status_code == 201


def test_inactive_staff_cannot_login_or_receive_token(client):
    test_client, session_factory = client
    _create_staff(session_factory, active=0)
    response = test_client.post(
        "/auth/login",
        data={"username": "staff@example.com", "password": "correct-password"},
    )
    assert response.status_code == 401
    assert "access_token" not in response.json()


def test_invalid_staff_password_is_rejected(client):
    test_client, session_factory = client
    _create_staff(session_factory)
    response = test_client.post(
        "/auth/login",
        data={"username": "staff@example.com", "password": "wrong-password"},
    )
    assert response.status_code == 401
    assert "access_token" not in response.json()


def test_login_endpoint_rate_limits_repeated_attempts(client, monkeypatch):
    test_client, _ = client
    monkeypatch.setattr(auth_routes, "MAX_LOGIN_ATTEMPTS", 2)
    for _ in range(2):
        assert test_client.post(
            "/auth/login", data={"username": "missing@example.com", "password": "wrong"}
        ).status_code == 401
    limited = test_client.post(
        "/auth/customer/login", data={"username": "missing@example.com", "password": "wrong"}
    )
    assert limited.status_code == 429
    assert int(limited.headers["Retry-After"]) > 0


def test_public_registration_endpoint_is_rate_limited(client, monkeypatch):
    test_client, _ = client
    monkeypatch.setattr(auth_routes, "MAX_REGISTRATIONS", 2)
    for index in range(2):
        response = test_client.post(
            "/auth/customer/register",
            json={
                "name": f"Customer {index}",
                "email": f"customer{index}@example.com",
                "password": "password123",
            },
        )
        assert response.status_code == 201
    limited = test_client.post(
        "/auth/customer/register",
        json={"name": "Third", "email": "third@example.com", "password": "password123"},
    )
    assert limited.status_code == 429


def test_production_configuration_fails_closed_without_real_secrets():
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        resolve_secret_key("production", None)
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        resolve_secret_key("production", DEVELOPMENT_SECRET_KEY)
    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        resolve_database_url("production", None)
    with pytest.raises(RuntimeError, match="database credentials"):
        resolve_database_url(
            "production",
            "postgresql://user:dev-only-change-me@localhost/restaurant_db",
        )


def test_development_configuration_requires_a_database_url():
    assert resolve_secret_key("development", None) == DEVELOPMENT_SECRET_KEY
    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        resolve_database_url("development", None)
    local_database_url = "postgresql://localhost/restaurant_db"
    assert resolve_database_url("development", local_database_url) == local_database_url


def test_staff_delete_preserves_audit_snapshot_with_foreign_keys_enabled():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _record):
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = session_factory()
    try:
        admin = models.Staff(
            name="Audit Admin",
            role=models.StaffRole.admin,
            email="audit-admin-delete@example.com",
            hashed_password="unused",
            active=1,
        )
        deleted_staff = models.Staff(
            name="Former Waiter",
            role=models.StaffRole.waiter,
            email="former-waiter@example.com",
            hashed_password="unused",
            active=1,
        )
        db.add_all([admin, deleted_staff])
        db.flush()
        original_log = models.AuditLog(
            staff_id=deleted_staff.id,
            staff_name=deleted_staff.name,
            role=deleted_staff.role.value,
            action="Completed order service",
        )
        db.add(original_log)
        db.commit()
        admin_id = admin.id
        deleted_staff_id = deleted_staff.id
        original_log_id = original_log.id

        delete_staff(deleted_staff_id, db, admin)

        assert db.query(models.Staff).filter_by(id=deleted_staff_id).count() == 0
        preserved_log = db.query(models.AuditLog).filter_by(id=original_log_id).one()
        assert preserved_log.staff_id is None
        assert preserved_log.staff_name == "Former Waiter"
        assert preserved_log.role == models.StaffRole.waiter.value
        assert preserved_log.action == "Completed order service"
        deletion_log = db.query(models.AuditLog).filter(
            models.AuditLog.action == "Deleted staff account former-waiter@example.com"
        ).one()
        assert deletion_log.staff_id == admin_id

        self_log = models.AuditLog(
            staff_id=admin_id,
            staff_name="Audit Admin",
            role=models.StaffRole.admin.value,
            action="Reviewed operations",
        )
        db.add(self_log)
        db.commit()
        self_log_id = self_log.id
        admin = db.query(models.Staff).filter_by(id=admin_id).one()
        delete_staff(admin_id, db, admin)

        assert db.query(models.Staff).filter_by(id=admin_id).count() == 0
        preserved_self_log = db.query(models.AuditLog).filter_by(id=self_log_id).one()
        assert preserved_self_log.staff_id is None
        assert preserved_self_log.staff_name == "Audit Admin"
        assert preserved_self_log.action == "Reviewed operations"
        self_delete_log = db.query(models.AuditLog).filter(
            models.AuditLog.action == "Deleted staff account audit-admin-delete@example.com"
        ).one()
        assert self_delete_log.staff_id is None
        assert self_delete_log.staff_name == "Audit Admin"
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def test_supabase_migration_does_not_print_connection_credentials(monkeypatch, capsys):
    connection_url = "postgresql://postgres:private-test-password@db.example:5432/restaurant"
    engine = Mock()
    connection_context = Mock()
    connection_context.__enter__ = Mock(return_value=Mock())
    connection_context.__exit__ = Mock(return_value=False)
    engine.connect.return_value = connection_context
    inspector = Mock()
    inspector.get_columns.return_value = [{"name": "customer_id"}, {"name": "entry_type"}]

    monkeypatch.setenv("SUPABASE_DATABASE_URL", connection_url)
    monkeypatch.setattr("sqlalchemy.create_engine", lambda *args, **kwargs: engine)
    monkeypatch.setattr("sqlalchemy.inspect", lambda _engine: inspector)
    script_path = Path(__file__).resolve().parents[1] / "migrate_waitlist_supabase.py"
    runpy.run_path(str(script_path), run_name="security_test_migration")

    output = capsys.readouterr().out
    assert "Connecting to configured database" in output
    assert connection_url not in output
    assert "private-test-password" not in output