from typing import Literal, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.exceptions import NotFoundError
from app.models.blueprint import Blueprint
from app.models.user import User
from app.schemas.blueprint import (
    BlueprintCreate,
    BlueprintListResponse,
    BlueprintResponse,
)

router = APIRouter(prefix="/api/blueprints", tags=["blueprints"])


@router.post("", response_model=BlueprintResponse, status_code=201)
def create_blueprint(
    body: BlueprintCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    blueprint = Blueprint(
        user_id=current_user.id,
        title=body.title,
        description=body.description,
        tags=body.tags,
        difficulty=body.difficulty,
        estimated_time=body.estimated_time,
        distance=body.distance,
        coordinates=body.coordinates,
        thumbnail_url=body.thumbnail_url,
    )
    db.add(blueprint)
    db.commit()
    db.refresh(blueprint)
    return blueprint


@router.get("", response_model=BlueprintListResponse)
def list_blueprints(
    tag: Optional[str] = Query(default=None, min_length=1),
    difficulty: Optional[int] = Query(default=None, ge=1, le=3),
    sort: Literal["latest", "popular"] = Query(default="latest"),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(Blueprint)
    if difficulty is not None:
        query = query.filter(Blueprint.difficulty == difficulty)

    if sort == "popular":
        query = query.order_by(
            Blueprint.download_count.desc(),
            Blueprint.created_at.desc(),
            Blueprint.id.desc(),
        )
    else:
        query = query.order_by(Blueprint.created_at.desc(), Blueprint.id.desc())

    offset = (page - 1) * size
    if tag is None:
        total = query.count()
        items = query.offset(offset).limit(size).all()
    else:
        tagged = [bp for bp in query.all() if tag in (bp.tags or [])]
        total = len(tagged)
        items = tagged[offset:offset + size]

    return BlueprintListResponse(items=items, total=total, page=page, size=size)


@router.get("/{blueprint_id}", response_model=BlueprintResponse)
def get_blueprint(
    blueprint_id: int,
    db: Session = Depends(get_db),
):
    blueprint = db.query(Blueprint).filter(Blueprint.id == blueprint_id).first()
    if not blueprint:
        raise NotFoundError(f"Blueprint {blueprint_id} not found")
    return blueprint
