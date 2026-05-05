"""FastAPI dependency injectors — current_user resolution from JWT."""
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import UnauthorizedError
from app.core.security import decode_access_token
from app.models.user import User

# tokenUrl is informational for OpenAPI; real issuance is via /api/auth/*/callback.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token", auto_error=False)


def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    if not token:
        raise UnauthorizedError("Not authenticated")

    payload = decode_access_token(token)
    sub = payload.get("sub")
    if sub is None:
        raise UnauthorizedError("Token missing subject")

    try:
        user_id = int(sub)
    except (TypeError, ValueError) as exc:
        raise UnauthorizedError("Invalid subject in token") from exc

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise UnauthorizedError("User no longer exists")
    return user
