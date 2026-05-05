"""OAuth 2.0 (authorization code flow) for Google and Kakao.

Flow:
  1. GET /api/auth/{provider}/authorize -> authorization_url (redirect target)
  2. Provider redirects back to /api/auth/{provider}/callback?code=...&state=...
  3. Server validates state, exchanges code for provider access_token, fetches
     userinfo, upserts a row in users, and returns an app-signed JWT.

Provider HTTP calls live in `_exchange_and_fetch_{provider}`. Tests monkey-patch
these helpers — no live HTTP in unit tests.

⚠️ SCAFFOLD-ONLY — NOT PRODUCTION READY. ⚠️

CSRF state is held in an in-process set (`_PENDING_STATES`). This is fine for a
single-worker dev server but is wrong for prod: it leaks memory on abandoned
flows, does not survive restarts, and breaks under multi-worker deployments.
Before any public deployment we must swap this for a persistent + TTL-bound
store (Redis / signed cookie / DB). Until then, treat the whole OAuth flow as
'scaffold / local dev only' — do not expose callback URLs to real users.

NOTE: refresh_token flow is deferred for MVP. See TokenResponse.
"""
import secrets
import threading
from typing import Literal
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.exceptions import EarthCanvasError, UnauthorizedError, ValidationError
from app.core.security import create_access_token
from app.models.user import User
from app.schemas.auth import AuthorizationURL, TokenResponse
from pydantic import BaseModel


class DevLoginRequest(BaseModel):
    email: str
    nickname: str = "DevUser"

router = APIRouter(prefix="/api/auth", tags=["auth"])

Provider = Literal["google", "kakao"]

_GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
_GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
_GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"

_KAKAO_AUTH_URL = "https://kauth.kakao.com/oauth/authorize"
_KAKAO_TOKEN_URL = "https://kauth.kakao.com/oauth/token"
_KAKAO_USERINFO_URL = "https://kapi.kakao.com/v2/user/me"


# ── Scaffold-only in-process state store ─────────────────────────────────────
# TODO(prod): replace with Redis/DB with TTL before public deployment.
# See module docstring: this does not survive restarts or multi-worker setups.
_PENDING_STATES: set[str] = set()
_PENDING_STATES_LOCK = threading.Lock()


def _issue_state() -> str:
    state = secrets.token_urlsafe(32)
    with _PENDING_STATES_LOCK:
        _PENDING_STATES.add(state)
    return state


def _consume_state(state: str | None) -> None:
    """Raise UnauthorizedError if state is missing / not pending. Single-use."""
    if not state:
        raise UnauthorizedError("Missing OAuth state")
    with _PENDING_STATES_LOCK:
        if state not in _PENDING_STATES:
            raise UnauthorizedError("Invalid or expired OAuth state")
        _PENDING_STATES.discard(state)


def _provider_config(provider: Provider) -> dict:
    if provider == "google":
        return {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "redirect_uri": settings.GOOGLE_REDIRECT_URI,
            "auth_url": _GOOGLE_AUTH_URL,
            "scope": "openid email profile",
        }
    if provider == "kakao":
        return {
            "client_id": settings.KAKAO_CLIENT_ID,
            "client_secret": settings.KAKAO_CLIENT_SECRET,
            "redirect_uri": settings.KAKAO_REDIRECT_URI,
            "auth_url": _KAKAO_AUTH_URL,
            "scope": "account_email profile_nickname",
        }
    raise ValidationError(f"Unsupported OAuth provider: {provider}")


def _build_authorization_url(provider: Provider) -> str:
    cfg = _provider_config(provider)
    state = _issue_state()
    params = {
        "client_id": cfg["client_id"],
        "redirect_uri": cfg["redirect_uri"],
        "response_type": "code",
        "scope": cfg["scope"],
        "state": state,
    }
    return f"{cfg['auth_url']}?{urlencode(params)}"


def _convert_provider_error(provider: str, exc: Exception) -> EarthCanvasError:
    """Convert raw httpx / JSON errors to our standard EarthCanvasError envelope.

    Keeps the response shape {detail, error_code} consistent with the rest of the API.
    """
    if isinstance(exc, httpx.TimeoutException):
        return UnauthorizedError(f"{provider} OAuth request timed out")
    if isinstance(exc, httpx.HTTPError):
        return UnauthorizedError(f"{provider} OAuth network error")
    if isinstance(exc, ValueError):
        # httpx .json() raises ValueError / json.JSONDecodeError (subclass) on bad bodies.
        return UnauthorizedError(f"{provider} OAuth returned malformed response")
    return UnauthorizedError(f"{provider} OAuth failed")


def _exchange_and_fetch_google(code: str) -> dict:
    """Exchange code for Google access token, fetch userinfo.

    Returns: {"email": str, "nickname": str}. Raises UnauthorizedError on failure.
    Test suites monkey-patch this whole function.
    """
    cfg = _provider_config("google")
    try:
        with httpx.Client(timeout=10.0) as client:
            token_resp = client.post(
                _GOOGLE_TOKEN_URL,
                data={
                    "code": code,
                    "client_id": cfg["client_id"],
                    "client_secret": cfg["client_secret"],
                    "redirect_uri": cfg["redirect_uri"],
                    "grant_type": "authorization_code",
                },
            )
            if token_resp.status_code != 200:
                raise UnauthorizedError("Google token exchange failed")
            provider_token = token_resp.json().get("access_token")
            if not provider_token:
                raise UnauthorizedError("Google token response missing access_token")

            user_resp = client.get(
                _GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {provider_token}"},
            )
            if user_resp.status_code != 200:
                raise UnauthorizedError("Google userinfo fetch failed")
            info = user_resp.json()
    except EarthCanvasError:
        raise
    except (httpx.TimeoutException, httpx.HTTPError, ValueError) as exc:
        raise _convert_provider_error("google", exc) from exc
    email = info.get("email")
    if not email:
        raise UnauthorizedError("Google profile missing email")
    nickname = info.get("name") or email.split("@")[0]
    return {"email": email, "nickname": nickname}


def _exchange_and_fetch_kakao(code: str) -> dict:
    cfg = _provider_config("kakao")
    try:
        with httpx.Client(timeout=10.0) as client:
            token_payload = {
                "code": code,
                "client_id": cfg["client_id"],
                "redirect_uri": cfg["redirect_uri"],
                "grant_type": "authorization_code",
            }
            if cfg["client_secret"]:
                token_payload["client_secret"] = cfg["client_secret"]
            token_resp = client.post(_KAKAO_TOKEN_URL, data=token_payload)
            if token_resp.status_code != 200:
                raise UnauthorizedError("Kakao token exchange failed")
            provider_token = token_resp.json().get("access_token")
            if not provider_token:
                raise UnauthorizedError("Kakao token response missing access_token")

            user_resp = client.get(
                _KAKAO_USERINFO_URL,
                headers={"Authorization": f"Bearer {provider_token}"},
            )
            if user_resp.status_code != 200:
                raise UnauthorizedError("Kakao userinfo fetch failed")
            info = user_resp.json()
    except EarthCanvasError:
        raise
    except (httpx.TimeoutException, httpx.HTTPError, ValueError) as exc:
        raise _convert_provider_error("kakao", exc) from exc
    account = info.get("kakao_account") or {}
    email = account.get("email")
    if not email:
        raise UnauthorizedError("Kakao profile missing email")
    profile = account.get("profile") or {}
    nickname = profile.get("nickname") or email.split("@")[0]
    return {"email": email, "nickname": nickname}


def _upsert_user(db: Session, email: str, nickname: str, provider: str) -> User:
    user = db.query(User).filter(User.email == email).first()
    if user:
        return user
    user = User(email=email, nickname=nickname, provider=provider)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/dev-login", response_model=TokenResponse)
def dev_login(body: DevLoginRequest, db: Session = Depends(get_db)):
    """Local-dev only: mint a JWT for any email. Disabled when settings.ALLOW_DEV_LOGIN is False.

    WARNING — 로컬 개발 전용. 운영에서는 반드시 ALLOW_DEV_LOGIN=false (기본값).
    환경변수 미설정 시 이 엔드포인트는 401을 반환한다. 운영 배포 전 env에서 ALLOW_DEV_LOGIN을
    제거하거나 false로 두어 자동 차단되도록 한다.

    Rationale: the only production path to a JWT is the OAuth callback, which requires
    live provider credentials. For local dev + integration tests we need a deterministic
    way to get a token without mocking the entire OAuth round-trip.

    NOTE: even the OAuth callback path is currently scaffold-only (see module docstring —
    state store is in-process). Do not expose either endpoint to real users yet.
    """
    if not settings.ALLOW_DEV_LOGIN:
        raise UnauthorizedError("Dev login is disabled")
    user = _upsert_user(db, email=str(body.email), nickname=body.nickname, provider="local")
    return TokenResponse(access_token=create_access_token(subject=user.id), token_type="bearer")


@router.get("/{provider}/authorize", response_model=AuthorizationURL)
def authorize(provider: Provider):
    return AuthorizationURL(authorization_url=_build_authorization_url(provider))


@router.get("/{provider}/callback", response_model=TokenResponse)
def callback(
    provider: Provider,
    code: str,
    state: str | None = None,
    db: Session = Depends(get_db),
):
    _consume_state(state)

    if provider == "google":
        profile = _exchange_and_fetch_google(code)
    elif provider == "kakao":
        profile = _exchange_and_fetch_kakao(code)
    else:
        raise ValidationError(f"Unsupported OAuth provider: {provider}")

    user = _upsert_user(db, email=profile["email"], nickname=profile["nickname"], provider=provider)
    token = create_access_token(subject=user.id)
    return TokenResponse(access_token=token, token_type="bearer")
