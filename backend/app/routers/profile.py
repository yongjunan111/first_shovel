from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.exceptions import ValidationError
from app.models.user import User
from app.schemas.profile import ProfileResponse, ProfileUpdate

router = APIRouter(prefix="/api/me", tags=["profile"])


@router.get("", response_model=ProfileResponse)
def get_profile(current_user: User = Depends(get_current_user)):
    return current_user


@router.patch("", response_model=ProfileResponse)
def update_profile(
    body: ProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if "nickname" in body.model_fields_set:
        if body.nickname is None:
            raise ValidationError("nickname cannot be null")
        current_user.nickname = body.nickname

    if "profile_image" in body.model_fields_set:
        current_user.profile_image = body.profile_image

    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return current_user
