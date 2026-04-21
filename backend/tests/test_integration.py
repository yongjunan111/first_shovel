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


def _ride_body(blueprint_id: int, target_lat: float = 37.5000, target_lng: float = 127.0000,
               rotation_angle: float = 0.0, scale: float = 1.0) -> dict:
    return {
        "blueprint_id": blueprint_id,
        "started_at": NOW,
        "target_lat": target_lat,
        "target_lng": target_lng,
        "rotation_angle": rotation_angle,
        "scale": scale,
    }


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

    # Stencil transform (preview)
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

    # Start ride — server computes + persists target_coordinates from the same params
    r = client.post("/api/rides", json=_ride_body(bp_id, target_lat=37.55, target_lng=127.10))
    assert r.status_code == 201
    started = r.json()
    ride_id = started["id"]
    assert started["target_coordinates"] == transformed, (
        "start_ride must persist stencil-transformed target_coordinates"
    )

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

    r = client.post("/api/rides", json=_ride_body(
        bp_id, target_lat=37.60, target_lng=127.05, rotation_angle=45, scale=2.0,
    ))
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
        r = client.post("/api/rides", json=_ride_body(bp_id))
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


# ── Golden path: transformed target scoring (result of decision B) ───────────

def test_transformed_target_scores_high_when_actual_matches_transform(client):
    """
    Golden path for decision B: when the user picks a far-away target with
    rotation+scale and actually follows the transformed path on the ground,
    the score must be high. Previously (scores.py:35 bug) the score was
    computed against the original blueprint and would collapse to ~0 because
    the actual path is hundreds of km away from the blueprint origin.
    """
    bp_id = create_blueprint(client)

    far_target_lat = 37.8000       # ~33 km north of blueprint origin
    far_target_lng = 127.2000      # ~18 km east
    rotation = 30.0
    scale = 1.5

    # Preview the stencil the user chose — this is where they "draw" on the map.
    r = client.post("/api/stencil/transform", json={
        "blueprint_id": bp_id,
        "target_lat": far_target_lat,
        "target_lng": far_target_lng,
        "rotation_angle": rotation,
        "scale": scale,
    })
    assert r.status_code == 200
    transformed = r.json()["transformed_coordinates"]

    # The transformed path must actually be far from the original blueprint,
    # otherwise this test wouldn't distinguish the bug from the fix.
    assert abs(transformed[0][0] - BLUEPRINT_COORDS[0][0]) > 0.1

    # Start ride with the same stencil params → server stores target_coordinates.
    r = client.post("/api/rides", json=_ride_body(
        bp_id, target_lat=far_target_lat, target_lng=far_target_lng,
        rotation_angle=rotation, scale=scale,
    ))
    assert r.status_code == 201
    assert r.json()["target_coordinates"] == transformed
    ride_id = r.json()["id"]

    # Rider perfectly follows the transformed path on the ground.
    r = client.put(f"/api/rides/{ride_id}/finish", json={
        "actual_coordinates": transformed,
        "finished_at": LATER,
        "distance": 1.0,
        "duration": 3600,
    })
    assert r.status_code == 200

    r = client.post("/api/scores", json={"ride_id": ride_id})
    assert r.status_code == 201
    body = r.json()
    assert body["score"] >= 95.0, (
        f"golden path score must be near 100 when actual matches target; got {body['score']}"
    )
    # Deviation must be tiny because target == actual.
    assert body["details"]["avg_deviation_m"] < 1.0


def test_target_coordinates_cannot_be_overridden_by_client(client):
    """Client-supplied target_coordinates must be ignored — server computes it."""
    bp_id = create_blueprint(client)
    bogus = [[0.0, 0.0], [1.0, 1.0]]
    payload = _ride_body(bp_id, target_lat=37.55, target_lng=127.10)
    payload["target_coordinates"] = bogus   # extra field — must not leak into server state
    r = client.post("/api/rides", json=payload)
    assert r.status_code == 201
    assert r.json()["target_coordinates"] != bogus


# ── Contract compatibility: stencil params are all optional ──────────────────

def test_ride_create_without_stencil_params_uses_blueprint_coords(client):
    """
    Back-compat contract: a client that only knows blueprint_id + started_at
    (no stencil transform) must still be able to start a ride. Server falls
    back to blueprint.coordinates as the target path.
    """
    bp_id = create_blueprint(client)

    r = client.post("/api/rides", json={
        "blueprint_id": bp_id,
        "started_at": NOW,
    })
    assert r.status_code == 201, r.json()
    body = r.json()
    assert body["target_coordinates"] == BLUEPRINT_COORDS, (
        "no-stencil path must persist blueprint.coordinates as target_coordinates"
    )

    # Rider follows the blueprint exactly → high score, confirming the
    # fallback target is actually used for scoring (not some empty/default).
    ride_id = body["id"]
    client.put(f"/api/rides/{ride_id}/finish", json={
        "actual_coordinates": BLUEPRINT_COORDS,
        "finished_at": LATER,
        "distance": 1.0,
        "duration": 3600,
    })
    r = client.post("/api/scores", json={"ride_id": ride_id})
    assert r.status_code == 201
    assert r.json()["score"] >= 95.0


def test_ride_create_rejects_half_provided_stencil_target(client):
    """
    If the client supplies only one of target_lat/target_lng, the request
    must fail (422) — ambiguous stencil intent. Both or neither.
    """
    bp_id = create_blueprint(client)

    # Only target_lat — must reject.
    r = client.post("/api/rides", json={
        "blueprint_id": bp_id,
        "started_at": NOW,
        "target_lat": 37.55,
    })
    assert r.status_code == 422
    assert r.json()["error_code"] == "VALIDATION_ERROR"

    # Only target_lng — must reject.
    r = client.post("/api/rides", json={
        "blueprint_id": bp_id,
        "started_at": NOW,
        "target_lng": 127.10,
    })
    assert r.status_code == 422
    assert r.json()["error_code"] == "VALIDATION_ERROR"


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
    r = client.post("/api/rides", json=_ride_body(bp_id))
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
    r = client.post("/api/rides", json=_ride_body(bp_id))
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
    r = client.post("/api/rides", json=_ride_body(bp_id))
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
