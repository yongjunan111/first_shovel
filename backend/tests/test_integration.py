"""
Integration tests: full Play → Score flow using TestClient + in-memory SQLite DB.

Scenarios:
  1. Happy path: blueprint → stencil transform → start ride → finish → score
  2. Transform + edited coordinates → ride → score
  3. Same blueprint, multiple rides → each gets its own score
  4. Error cases: 404s, double-finish, unfinished ride scoring
"""
import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base, get_db
from app.models.user import User
from main import app

# ── In-memory SQLite test DB ─────────────────────────────────────────────────

TEST_DB_URL = "sqlite:///./test_integration.db"

engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    db = TestingSession()
    # Seed dev user (id=1)
    if not db.query(User).filter(User.id == 1).first():
        db.add(User(email="dev@earthcanvas.local", nickname="DevUser", provider="local"))
        db.commit()
    db.close()
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(setup_db):
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ── helpers ───────────────────────────────────────────────────────────────────

BLUEPRINT_COORDS = [
    [37.5000, 127.0000],
    [37.5010, 127.0010],
    [37.5020, 127.0020],
    [37.5030, 127.0010],
    [37.5040, 127.0000],
]

NOW = datetime(2026, 4, 9, 10, 0, 0, tzinfo=timezone.utc).isoformat()
LATER = datetime(2026, 4, 9, 11, 0, 0, tzinfo=timezone.utc).isoformat()


def create_blueprint(client) -> int:
    """Directly insert a blueprint via the DB (partner API not yet available)."""
    db = TestingSession()
    from app.models.blueprint import Blueprint
    bp = Blueprint(
        user_id=1,
        title="Test Route",
        coordinates=BLUEPRINT_COORDS,
        distance=1.0,
    )
    db.add(bp)
    db.commit()
    db.refresh(bp)
    bp_id = bp.id
    db.close()
    return bp_id


# ── Scenario 1: happy path ────────────────────────────────────────────────────

def test_happy_path_full_flow(client):
    bp_id = create_blueprint(client)

    # Stencil transform
    r = client.post("/api/stencil/transform", json={
        "blueprint_id": bp_id,
        "target_lat": 37.55,
        "target_lng": 127.10,
        "rotation_angle": 0,
        "scale": 1.0,
    })
    assert r.status_code == 200
    transformed = r.json()["transformed_coordinates"]
    assert len(transformed) == len(BLUEPRINT_COORDS)

    # Start ride
    r = client.post("/api/rides", json={"blueprint_id": bp_id, "started_at": NOW})
    assert r.status_code == 201
    ride_id = r.json()["id"]

    # Finish ride with transformed coords as actual path
    r = client.put(f"/api/rides/{ride_id}/finish", json={
        "actual_coordinates": transformed,
        "finished_at": LATER,
        "distance": 1.0,
        "duration": 3600,
    })
    assert r.status_code == 200
    assert r.json()["finished_at"] is not None

    # Score
    r = client.post("/api/scores", json={"ride_id": ride_id})
    assert r.status_code == 201
    body = r.json()
    assert 0 <= body["score"] <= 100
    assert body["details"]["completion_rate"] > 0


# ── Scenario 2: transform + manual edit → ride → score ───────────────────────

def test_transform_with_scale_and_rotation(client):
    bp_id = create_blueprint(client)

    r = client.post("/api/stencil/transform", json={
        "blueprint_id": bp_id,
        "target_lat": 37.60,
        "target_lng": 127.05,
        "rotation_angle": 45,
        "scale": 2.0,
    })
    assert r.status_code == 200
    coords = r.json()["transformed_coordinates"]

    r = client.post("/api/rides", json={"blueprint_id": bp_id, "started_at": NOW})
    ride_id = r.json()["id"]

    r = client.put(f"/api/rides/{ride_id}/finish", json={
        "actual_coordinates": coords,
        "finished_at": LATER,
        "distance": 2.0,
        "duration": 7200,
    })
    assert r.status_code == 200

    r = client.post("/api/scores", json={"ride_id": ride_id})
    assert r.status_code == 201
    assert r.json()["score"] >= 0


# ── Scenario 3: same blueprint, multiple rides get separate scores ────────────

def test_multiple_rides_same_blueprint(client):
    bp_id = create_blueprint(client)
    scores = []

    for i in range(3):
        r = client.post("/api/rides", json={"blueprint_id": bp_id, "started_at": NOW})
        ride_id = r.json()["id"]

        # Slightly different actual path each time
        offset = i * 0.0001
        actual = [[lat + offset, lng] for lat, lng in BLUEPRINT_COORDS]

        client.put(f"/api/rides/{ride_id}/finish", json={
            "actual_coordinates": actual,
            "finished_at": LATER,
            "distance": 1.0,
            "duration": 3600,
        })
        r = client.post("/api/scores", json={"ride_id": ride_id})
        assert r.status_code == 201
        scores.append(r.json()["score"])

    # All three scores recorded; best deviation (i=0) should score highest
    assert scores[0] >= scores[1] >= scores[2]

    # Ranking returns 3 entries
    r = client.get(f"/api/scores/ranking/{bp_id}")
    assert r.status_code == 200
    assert len(r.json()) == 3


# ── Error cases ───────────────────────────────────────────────────────────────

def test_404_blueprint_not_found(client):
    r = client.post("/api/stencil/transform", json={
        "blueprint_id": 9999,
        "target_lat": 37.5,
        "target_lng": 127.0,
        "rotation_angle": 0,
        "scale": 1.0,
    })
    assert r.status_code == 404
    assert r.json()["error_code"] == "NOT_FOUND"


def test_double_finish_rejected(client):
    bp_id = create_blueprint(client)
    r = client.post("/api/rides", json={"blueprint_id": bp_id, "started_at": NOW})
    ride_id = r.json()["id"]

    finish_body = {
        "actual_coordinates": BLUEPRINT_COORDS,
        "finished_at": LATER,
        "distance": 1.0,
        "duration": 3600,
    }
    client.put(f"/api/rides/{ride_id}/finish", json=finish_body)
    r = client.put(f"/api/rides/{ride_id}/finish", json=finish_body)
    assert r.status_code == 400
    assert r.json()["error_code"] == "BAD_REQUEST"


def test_score_unfinished_ride(client):
    bp_id = create_blueprint(client)
    r = client.post("/api/rides", json={"blueprint_id": bp_id, "started_at": NOW})
    ride_id = r.json()["id"]

    r = client.post("/api/scores", json={"ride_id": ride_id})
    assert r.status_code == 400
    assert r.json()["error_code"] == "BAD_REQUEST"


def test_scale_out_of_range(client):
    bp_id = create_blueprint(client)
    r = client.post("/api/stencil/transform", json={
        "blueprint_id": bp_id,
        "target_lat": 37.5,
        "target_lng": 127.0,
        "rotation_angle": 0,
        "scale": 999.0,   # way over the 10x limit
    })
    assert r.status_code == 422
    assert r.json()["error_code"] == "VALIDATION_ERROR"


def test_duplicate_score_returns_existing(client):
    bp_id = create_blueprint(client)
    r = client.post("/api/rides", json={"blueprint_id": bp_id, "started_at": NOW})
    ride_id = r.json()["id"]
    client.put(f"/api/rides/{ride_id}/finish", json={
        "actual_coordinates": BLUEPRINT_COORDS,
        "finished_at": LATER,
        "distance": 1.0,
        "duration": 3600,
    })
    r1 = client.post("/api/scores", json={"ride_id": ride_id})
    r2 = client.post("/api/scores", json={"ride_id": ride_id})
    assert r1.status_code == 201
    assert r2.status_code == 201
    assert r1.json()["id"] == r2.json()["id"]
