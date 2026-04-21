from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.core.exceptions import NotFoundError, BadRequestError, ValidationError
from app.models.ride import Ride
from app.models.blueprint import Blueprint
from app.schemas.ride import RideCreate, RideFinish, RideResponse
from app.services.stencil import transform_coordinates

router = APIRouter(prefix="/api/rides", tags=["rides"])

# TODO: replace with real JWT auth (Day 4)
TEMP_USER_ID = 1

_SCALE_MIN, _SCALE_MAX = 0.1, 10.0


@router.post("", response_model=RideResponse, status_code=201)
def start_ride(body: RideCreate, db: Session = Depends(get_db)):
    if not (_SCALE_MIN <= body.scale <= _SCALE_MAX):
        raise ValidationError(f"scale must be between {_SCALE_MIN} and {_SCALE_MAX}")

    bp = db.query(Blueprint).filter(Blueprint.id == body.blueprint_id).first()
    if not bp:
        raise NotFoundError(f"Blueprint {body.blueprint_id} not found")
    if not bp.coordinates or len(bp.coordinates) < 2:
        raise ValidationError("Blueprint has insufficient coordinates for ride")

    if body.target_lat is None and body.target_lng is None:
        # Back-compat path: client didn't pick a map target, use blueprint as-is.
        target_coordinates = list(bp.coordinates)
    else:
        target_coordinates = transform_coordinates(
            bp.coordinates,
            body.target_lat,
            body.target_lng,
            body.rotation_angle,
            body.scale,
        )

    ride = Ride(
        user_id=TEMP_USER_ID,
        blueprint_id=body.blueprint_id,
        target_coordinates=target_coordinates,
        started_at=body.started_at,
    )
    db.add(ride)
    db.commit()
    db.refresh(ride)
    return ride


@router.put("/{ride_id}/finish", response_model=RideResponse)
def finish_ride(ride_id: int, body: RideFinish, db: Session = Depends(get_db)):
    ride = db.query(Ride).filter(Ride.id == ride_id, Ride.user_id == TEMP_USER_ID).first()
    if not ride:
        raise NotFoundError(f"Ride {ride_id} not found")
    if ride.finished_at:
        raise BadRequestError("Ride already finished")
    if len(body.actual_coordinates) < 2:
        raise BadRequestError("actual_coordinates must have at least 2 points")

    ride.actual_coordinates = body.actual_coordinates
    ride.finished_at = body.finished_at
    ride.distance = body.distance
    ride.duration = body.duration
    db.commit()
    db.refresh(ride)
    return ride


@router.get("", response_model=List[RideResponse])
def list_rides(db: Session = Depends(get_db)):
    return db.query(Ride).filter(Ride.user_id == TEMP_USER_ID).all()


@router.get("/{ride_id}", response_model=RideResponse)
def get_ride(ride_id: int, db: Session = Depends(get_db)):
    ride = db.query(Ride).filter(Ride.id == ride_id, Ride.user_id == TEMP_USER_ID).first()
    if not ride:
        raise NotFoundError(f"Ride {ride_id} not found")
    return ride
