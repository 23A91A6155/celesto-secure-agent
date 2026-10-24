"""Integration tests for the Run Ledger API endpoints."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import get_db, init_db
from app.models import Base

# Set up an isolated SQLite in-memory database with StaticPool for testing
test_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_test_db():
    """Create all tables and seed row before each test."""
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    init_db(target_engine=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


def test_list_runs_includes_seed():
    """Verify GET /api/runs includes the initial seed row sbx-seeddemo1."""
    response = client.get("/api/runs")
    assert response.status_code == 200
    runs = response.json()
    assert isinstance(runs, list)
    assert len(runs) >= 1

    seed = next((r for r in runs if r["sandbox_name"] == "sbx-seeddemo1"), None)
    assert seed is not None
    assert seed["state"] == "deleted"
    assert seed["execution_target"] == "celesto_sandbox"


def test_create_valid_run():
    """Verify POST /api/runs with valid payload returns HTTP 201."""
    payload = {
        "run_id": "run-test-12345",
        "sandbox_name": "sbx-abcdefgh1234",
        "problem_id": "celesto-agent-task",
        "state": "created",
        "execution_target": "celesto_sandbox",
    }
    response = client.post("/api/runs", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["run_id"] == "run-test-12345"
    assert data["sandbox_name"] == "sbx-abcdefgh1234"
    assert data["execution_target"] == "celesto_sandbox"


def test_reject_invalid_execution_target():
    """Verify POST /api/runs rejects non-celesto execution targets like 'host'."""
    payload = {
        "run_id": "run-invalid-target",
        "sandbox_name": "sbx-validname1234",
        "problem_id": "celesto-agent-task",
        "state": "created",
        "execution_target": "host",
    }
    response = client.post("/api/runs", json=payload)
    assert response.status_code == 400
    data = response.json()
    assert "ValidationError" in str(data) or "error" in data


def test_reject_invalid_state():
    """Verify POST /api/runs rejects invalid states like 'unknown'."""
    payload = {
        "run_id": "run-invalid-state",
        "sandbox_name": "sbx-validname1234",
        "problem_id": "celesto-agent-task",
        "state": "invalid_state",
        "execution_target": "celesto_sandbox",
    }
    response = client.post("/api/runs", json=payload)
    assert response.status_code == 400


def test_reject_invalid_sandbox_name():
    """Verify POST /api/runs rejects sandbox names not matching ^sbx-[a-z0-9]{8,}$."""
    # Too short
    res1 = client.post("/api/runs", json={
        "run_id": "run-short-name",
        "sandbox_name": "sbx-short",
        "problem_id": "task",
        "state": "created",
        "execution_target": "celesto_sandbox",
    })
    assert res1.status_code == 400

    # Uppercase chars
    res2 = client.post("/api/runs", json={
        "run_id": "run-upper-name",
        "sandbox_name": "sbx-ABCDEFGH1234",
        "problem_id": "task",
        "state": "created",
        "execution_target": "celesto_sandbox",
    })
    assert res2.status_code == 400

    # No sbx- prefix
    res3 = client.post("/api/runs", json={
        "run_id": "run-no-prefix",
        "sandbox_name": "abcdefgh1234",
        "problem_id": "task",
        "state": "created",
        "execution_target": "celesto_sandbox",
    })
    assert res3.status_code == 400


def test_reject_duplicate_run_id():
    """Verify POST /api/runs rejects duplicate run_id."""
    payload = {
        "run_id": "run-duplicate-check",
        "sandbox_name": "sbx-dupcheck1234",
        "problem_id": "task",
        "state": "created",
        "execution_target": "celesto_sandbox",
    }
    res1 = client.post("/api/runs", json=payload)
    assert res1.status_code == 201

    res2 = client.post("/api/runs", json=payload)
    assert res2.status_code == 400
    assert "DuplicateRunId" in str(res2.json())


def test_seed_idempotency():
    """Verify re-running init_db does not create duplicate seed entries."""
    init_db(target_engine=test_engine)
    init_db(target_engine=test_engine)
    response = client.get("/api/runs")
    runs = response.json()
    seed_runs = [r for r in runs if r["run_id"] == "run-seed-0001"]
    assert len(seed_runs) == 1
