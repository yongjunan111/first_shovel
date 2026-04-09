from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.blueprint import Blueprint
from app.schemas.stencil import StencilTransformRequest, StencilTransformResponse, Bounds, Center
from app.services.stencil import transform_coordinates, compute_bounds, compute_center

router = APIRouter(prefix="/api/stencil", tags=["stencil"])


def _get_blueprint_or_404(blueprint_id: int, db: Session) -> Blueprint:
    bp = db.query(Blueprint).filter(Blueprint.id == blueprint_id).first()
    if not bp:
        raise HTTPException(status_code=404, detail="Blueprint not found")
    return bp


@router.post("/transform", response_model=StencilTransformResponse)
def transform(body: StencilTransformRequest, db: Session = Depends(get_db)):
    bp = _get_blueprint_or_404(body.blueprint_id, db)

    transformed = transform_coordinates(
        bp.coordinates,
        body.target_lat,
        body.target_lng,
        body.rotation_angle,
        body.scale,
    )

    return StencilTransformResponse(
        transformed_coordinates=transformed,
        bounds=Bounds(**compute_bounds(transformed)),
        center=Center(**compute_center(transformed)),
    )


@router.get("/preview/{blueprint_id}", response_model=StencilTransformResponse)
def preview(
    blueprint_id: int,
    lat: float,
    lng: float,
    angle: float = 0.0,
    scale: float = 1.0,
    db: Session = Depends(get_db),
):
    bp = _get_blueprint_or_404(blueprint_id, db)

    transformed = transform_coordinates(bp.coordinates, lat, lng, angle, scale)

    return StencilTransformResponse(
        transformed_coordinates=transformed,
        bounds=Bounds(**compute_bounds(transformed)),
        center=Center(**compute_center(transformed)),
    )
