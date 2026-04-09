from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.models.ride import Ride
from app.models.blueprint import Blueprint
from app.schemas.ride import RideCreate, RideFinish, RideResponse

router = APIRouter(prefix="/api/rides", tags=["rides"])

# TODO: replace with real JWT auth (Day 4)
TEMP_USER_ID = 1


@router.post("", response_model=RideResponse, status_code=201)
def start_ride(body: RideCreate, db: Session = Depends(get_db)):
    bp = db.query(Blueprint).filter(Blueprint.id == body.blueprint_id).first()
    if not bp:
        raise HTTPException(status_code=404, detail="Blueprint not found")

    ride = Ride(
        user_id=TEMP_USER_ID,
        blueprint_id=body.blueprint_id,
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
        raise HTTPException(status_code=404, detail="Ride not found")
    if ride.finished_at:
        raise HTTPException(status_code=400, detail="Ride already finished")

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
        raise HTTPException(status_code=404, detail="Ride not found")
    return ride
