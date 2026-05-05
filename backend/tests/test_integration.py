"""
Integration tests: full Play → Score flow using TestClient + file-backed SQLite DB.

Auth contract: `get_current_user` is overridden via `app.dependency_overrides`
to a test user, so the tests exercise ownership logic without needing a
real JWT. Separate tests cover the 401 / bad-token paths directly.

Scenarios:
  1. Happy path: blueprint → stencil transform → start ride → finish → score
  2. Transform + edited coordinates → ride → score
  3. Same blueprint, multiple rides → each gets its own score
  4. Error cases: 404s, double-finish, unfinished ride scoring
  5. Auth: 401 when no token / bad token, cross-user ride/score isolation
"""
import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base, get_db
from app.core.deps import get_current_user
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
    # Seed the primary test user (id=1). Ownership tests add a second user.
    if not db.query(User).filter(User.id == 1).first():
        db.add(User(email="tester@earthcanvas.local", nickname="Tester", provider="local"))
        db.commit()
    db.close()
    yield
    Base.metadata.drop_all(bind=engine)


def _primary_user() -> User:
    db = TestingSession()
    try:
        return db.query(User).filter(User.id == 1).one()
    finally:
        db.close()


@pytest.fixture
def client(setup_db):
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = _primary_user
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def unauth_client(setup_db):
    """Client with real get_current_user — used to exercise 401 paths."""
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


def create_blueprint(client, user_id: int = 1) -> int:
    """Directly insert a blueprint via the DB for lower-level Play/Score tests."""
    db = TestingSession()
    from app.models.blueprint import Blueprint
    bp = Blueprint(
        user_id=user_id,
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


def _blueprint_body(**overrides) -> dict:
    body = {
        "title": "Han River Fox",
        "description": "A short fox-shaped route near the river",
        "tags": ["animal", "river"],
        "difficulty": 2,
        "estimated_time": 35,
        "distance": 3.2,
        "coordinates": BLUEPRINT_COORDS,
        "thumbnail_url": "https://example.com/fox.png",
    }
    body.update(overrides)
    return body


# ── Create API: blueprint list/detail/create ──────────────────────────────────

def test_blueprint_create_requires_auth(unauth_client):
    r = unauth_client.post("/api/blueprints", json=_blueprint_body())
    assert r.status_code == 401
    assert r.json()["error_code"] == "UNAUTHORIZED"


def test_blueprint_create_and_detail(client):
    r = client.post("/api/blueprints", json=_blueprint_body())
    assert r.status_code == 201, r.text
    created = r.json()
    assert created["id"] > 0
    assert created["user_id"] == 1
    assert created["user"]["nickname"] == "Tester"
    assert created["title"] == "Han River Fox"
    assert created["tags"] == ["animal", "river"]
    assert created["coordinates"] == BLUEPRINT_COORDS

    detail = client.get(f"/api/blueprints/{created['id']}")
    assert detail.status_code == 200, detail.text
    assert detail.json() == created


def test_blueprints_list_filters_and_pages(client):
    first = client.post("/api/blueprints", json=_blueprint_body(title="Fox", tags=["animal"], difficulty=2))
    second = client.post(
        "/api/blueprints",
        json=_blueprint_body(title="Mountain", tags=["mountain"], difficulty=3),
    )
    assert first.status_code == 201, first.text
    assert second.status_code == 201, second.text

    r = client.get("/api/blueprints", params={"tag": "animal", "difficulty": 2, "page": 1, "size": 1})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total"] == 1
    assert body["page"] == 1
    assert body["size"] == 1
    assert [item["title"] for item in body["items"]] == ["Fox"]


def test_blueprint_detail_404(client):
    r = client.get("/api/blueprints/9999")
    assert r.status_code == 404
    assert r.json()["error_code"] == "NOT_FOUND"


def test_blueprint_create_rejects_invalid_coordinates(client):
    r = client.post("/api/blueprints", json=_blueprint_body(coordinates=[[37.5, 127.0]]))
    assert r.status_code == 422
    assert r.json()["error_code"] == "VALIDATION_ERROR"


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


# ── Auth: 401 shape + bad-token shape use Day 4 error envelope ───────────────

def test_rides_list_requires_auth(unauth_client):
    r = unauth_client.get("/api/rides")
    assert r.status_code == 401
    body = r.json()
    assert body["error_code"] == "UNAUTHORIZED"
    assert "detail" in body


def test_rides_list_rejects_bad_token(unauth_client):
    r = unauth_client.get("/api/rides", headers={"Authorization": "Bearer not-a-real-token"})
    assert r.status_code == 401
    assert r.json()["error_code"] == "UNAUTHORIZED"


def test_scores_get_requires_auth(unauth_client):
    r = unauth_client.get("/api/scores/1")
    assert r.status_code == 401
    assert r.json()["error_code"] == "UNAUTHORIZED"


# ── Auth: valid-JWT round trip via dev-login ─────────────────────────────────

def test_dev_login_issues_usable_jwt(unauth_client, monkeypatch):
    # settings.ALLOW_DEV_LOGIN defaults to False (prod-safe). This test opts in.
    from app.core import config
    monkeypatch.setattr(config.settings, "ALLOW_DEV_LOGIN", True)

    r = unauth_client.post("/api/auth/dev-login", json={"email": "alice@example.com", "nickname": "Alice"})
    assert r.status_code == 200, r.json()
    body = r.json()
    assert body["token_type"] == "bearer"
    token = body["access_token"]
    assert token

    # Token must unlock an authenticated endpoint.
    r = unauth_client.get("/api/rides", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json() == []   # Alice has no rides yet


def test_dev_login_disabled_by_default_returns_401(unauth_client):
    """With no settings override, ALLOW_DEV_LOGIN must default to False → 401."""
    from app.core import config
    assert config.settings.ALLOW_DEV_LOGIN is False, (
        "ALLOW_DEV_LOGIN default must be False so prod env-less config auto-disables dev-login"
    )
    r = unauth_client.post(
        "/api/auth/dev-login",
        json={"email": "nope@example.com", "nickname": "Nope"},
    )
    assert r.status_code == 401
    assert r.json()["error_code"] == "UNAUTHORIZED"


# ── Auth: cross-user ride/score isolation ────────────────────────────────────

def test_cross_user_ride_access_is_404(unauth_client):
    """User A creates a ride. User B gets 404 (not 200, not 403) on read/finish/score."""
    # Seed user B
    db = TestingSession()
    try:
        if not db.query(User).filter(User.id == 2).first():
            db.add(User(id=2, email="b@earthcanvas.local", nickname="UserB", provider="local"))
            db.commit()
    finally:
        db.close()

    # A starts + finishes a ride
    def user_a():
        return _primary_user()

    def user_b():
        db = TestingSession()
        try:
            return db.query(User).filter(User.id == 2).one()
        finally:
            db.close()

    bp_id = create_blueprint(unauth_client)

    app.dependency_overrides[get_current_user] = user_a
    r = unauth_client.post("/api/rides", json=_ride_body(bp_id))
    assert r.status_code == 201
    ride_id = r.json()["id"]
    r = unauth_client.put(f"/api/rides/{ride_id}/finish", json={
        "actual_coordinates": BLUEPRINT_COORDS,
        "finished_at": LATER,
        "distance": 1.0,
        "duration": 3600,
    })
    assert r.status_code == 200

    # B cannot see A's ride
    app.dependency_overrides[get_current_user] = user_b
    r = unauth_client.get(f"/api/rides/{ride_id}")
    assert r.status_code == 404
    # B cannot finish A's ride (already finished, but ownership beats state)
    r = unauth_client.put(f"/api/rides/{ride_id}/finish", json={
        "actual_coordinates": BLUEPRINT_COORDS,
        "finished_at": LATER,
        "distance": 1.0,
        "duration": 3600,
    })
    assert r.status_code == 404
    # B cannot score A's ride
    r = unauth_client.post("/api/scores", json={"ride_id": ride_id})
    assert r.status_code == 404
    # B's own ride list is empty
    r = unauth_client.get("/api/rides")
    assert r.status_code == 200
    assert r.json() == []


# ── Auth: OAuth token exchange is mockable ───────────────────────────────────

def _get_state_from_authorize(unauth_client, provider: str) -> str:
    """Drive /authorize to obtain a valid single-use state for /callback tests."""
    from urllib.parse import parse_qs, urlparse

    r = unauth_client.get(f"/api/auth/{provider}/authorize")
    assert r.status_code == 200, r.json()
    url = r.json()["authorization_url"]
    qs = parse_qs(urlparse(url).query)
    assert "state" in qs and qs["state"][0], f"authorize must include non-empty state: {url}"
    return qs["state"][0]


def test_google_oauth_callback_mints_jwt_when_provider_fetch_mocked(unauth_client, monkeypatch):
    """Patch _exchange_and_fetch_google so no real HTTP call is made.

    Confirms the callback wiring: code + state → (mocked) profile → upsert user → JWT.
    """
    from app.routers import auth as auth_router

    def fake_fetch(code: str):
        assert code == "fake-code"
        return {"email": "newbie@gmail.com", "nickname": "Newbie"}

    monkeypatch.setattr(auth_router, "_exchange_and_fetch_google", fake_fetch)

    state = _get_state_from_authorize(unauth_client, "google")
    r = unauth_client.get("/api/auth/google/callback", params={"code": "fake-code", "state": state})
    assert r.status_code == 200, r.json()
    body = r.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]

    # Use the token to hit an authenticated endpoint.
    r = unauth_client.get("/api/rides", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert r.status_code == 200


def test_google_authorize_url_contains_expected_params(unauth_client, monkeypatch):
    # Provide a stable client_id so the generated URL is deterministic.
    from app.core import config
    monkeypatch.setattr(config.settings, "GOOGLE_CLIENT_ID", "test-client-id")
    r = unauth_client.get("/api/auth/google/authorize")
    assert r.status_code == 200
    url = r.json()["authorization_url"]
    assert "accounts.google.com" in url
    assert "client_id=test-client-id" in url
    assert "response_type=code" in url
    # CSRF state must be present and non-empty (scaffold-only in-process store).
    assert "state=" in url
    from urllib.parse import parse_qs, urlparse
    qs = parse_qs(urlparse(url).query)
    assert qs["state"][0], "state must be non-empty"


def test_kakao_oauth_callback_mints_jwt_when_provider_fetch_mocked(unauth_client, monkeypatch):
    from app.routers import auth as auth_router

    def fake_fetch(code: str):
        return {"email": "k@kakao.com", "nickname": "Kakao"}

    monkeypatch.setattr(auth_router, "_exchange_and_fetch_kakao", fake_fetch)

    state = _get_state_from_authorize(unauth_client, "kakao")
    r = unauth_client.get("/api/auth/kakao/callback", params={"code": "whatever", "state": state})
    assert r.status_code == 200
    assert r.json()["access_token"]


# ── OAuth state (scaffold-only) — missing / mismatched / replay ─────────────

def test_callback_without_state_returns_401(unauth_client, monkeypatch):
    """Callback without `state` must 401 via the Day 4 error envelope.

    Ensures CSRF state is actually consumed — provider fetch must not even run.
    """
    from app.routers import auth as auth_router

    def must_not_be_called(code: str):
        raise AssertionError("provider fetch must not run when state is missing")

    monkeypatch.setattr(auth_router, "_exchange_and_fetch_google", must_not_be_called)

    r = unauth_client.get("/api/auth/google/callback", params={"code": "fake-code"})
    assert r.status_code == 401
    body = r.json()
    assert body["error_code"] == "UNAUTHORIZED"
    assert "state" in body["detail"].lower()


def test_callback_with_mismatched_state_returns_401(unauth_client, monkeypatch):
    from app.routers import auth as auth_router

    def must_not_be_called(code: str):
        raise AssertionError("provider fetch must not run on bad state")

    monkeypatch.setattr(auth_router, "_exchange_and_fetch_google", must_not_be_called)

    r = unauth_client.get(
        "/api/auth/google/callback",
        params={"code": "fake-code", "state": "never-issued-this"},
    )
    assert r.status_code == 401
    assert r.json()["error_code"] == "UNAUTHORIZED"


def test_callback_state_is_single_use(unauth_client, monkeypatch):
    """Replaying the same state after a successful callback must fail."""
    from app.routers import auth as auth_router

    monkeypatch.setattr(
        auth_router, "_exchange_and_fetch_google",
        lambda code: {"email": "reuse@gmail.com", "nickname": "Reuse"},
    )

    state = _get_state_from_authorize(unauth_client, "google")
    r = unauth_client.get("/api/auth/google/callback", params={"code": "c", "state": state})
    assert r.status_code == 200

    # Replay — same state must be rejected.
    r = unauth_client.get("/api/auth/google/callback", params={"code": "c", "state": state})
    assert r.status_code == 401
    assert r.json()["error_code"] == "UNAUTHORIZED"


# ── OAuth provider network/JSON errors → Day 4 error envelope ────────────────

def test_callback_provider_timeout_returns_401_envelope(unauth_client, monkeypatch):
    """If the provider fetch raises httpx.TimeoutException, convert to UnauthorizedError."""
    import httpx
    from app.routers import auth as auth_router

    def boom(code: str):
        # Route through the real error converter path by raising from inside the helper.
        # The helper itself swallows httpx.* and raises UnauthorizedError; emulate that.
        raise auth_router._convert_provider_error("google", httpx.TimeoutException("simulated"))

    monkeypatch.setattr(auth_router, "_exchange_and_fetch_google", boom)

    state = _get_state_from_authorize(unauth_client, "google")
    r = unauth_client.get("/api/auth/google/callback", params={"code": "c", "state": state})
    assert r.status_code == 401
    body = r.json()
    assert body["error_code"] == "UNAUTHORIZED"
    assert "detail" in body


def test_provider_helper_converts_timeout_httperror_and_json_errors():
    """Direct unit-level check: _exchange_and_fetch_google wraps httpx/JSON errors."""
    import httpx
    from app.routers import auth as auth_router
    from app.core.exceptions import UnauthorizedError

    class _BoomClient:
        def __init__(self, exc):
            self._exc = exc
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False
        def post(self, *a, **kw):
            raise self._exc
        def get(self, *a, **kw):
            raise self._exc

    for exc in (httpx.TimeoutException("t"), httpx.HTTPError("net"), ValueError("json")):
        def _client_factory(exc=exc, *a, **kw):
            return _BoomClient(exc)

        import pytest as _pytest
        with monkeypatched_httpx(_client_factory):
            with _pytest.raises(UnauthorizedError):
                auth_router._exchange_and_fetch_google("any-code")


from contextlib import contextmanager


@contextmanager
def monkeypatched_httpx(factory):
    """Swap httpx.Client inside auth_router for a boom-factory during the block."""
    from app.routers import auth as auth_router
    original = auth_router.httpx.Client
    auth_router.httpx.Client = factory
    try:
        yield
    finally:
        auth_router.httpx.Client = original


# ── Ranking is intentionally public (no auth) ────────────────────────────────

def test_ranking_is_public_no_auth(unauth_client):
    """/api/scores/ranking/{blueprint_id} must NOT require a JWT — public leaderboard."""
    bp_id = create_blueprint(unauth_client)
    r = unauth_client.get(f"/api/scores/ranking/{bp_id}")
    assert r.status_code == 200, r.json()
    assert isinstance(r.json(), list)


# ── JWT secret backward-compat (SECRET_KEY alias) ────────────────────────────

def test_secret_key_alias_promoted_to_jwt_secret_key(monkeypatch):
    """Legacy SECRET_KEY env must promote to JWT_SECRET_KEY when the latter is unset.

    Guards against silent fallback to the insecure 'change-me-in-production' default
    for deployments that already rely on the older env name.
    """
    # Keep the real .env from leaking in.
    monkeypatch.setenv("SECRET_KEY", "legacy-secret-xyz")
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
    # Force development so the production guard doesn't trip in a different path.
    monkeypatch.setenv("ENV", "development")

    from app.core.config import Settings
    s = Settings(_env_file=None)  # don't read .env — rely on our patched env vars
    assert s.JWT_SECRET_KEY == "legacy-secret-xyz"


def test_production_env_refuses_default_jwt_secret(monkeypatch):
    monkeypatch.setenv("ENV", "production")
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
    monkeypatch.delenv("SECRET_KEY", raising=False)

    import pytest as _pytest
    from app.core.config import Settings
    with _pytest.raises(ValueError):
        Settings(_env_file=None)
