from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.models.score import Score
from app.models.ride import Ride
from app.models.blueprint import Blueprint
from app.schemas.score import ScoreRequest, ScoreResponse, RankingEntry
from app.services.scoring import compute_score

router = APIRouter(prefix="/api/scores", tags=["scores"])

# TODO: replace with real JWT auth (Day 4)
TEMP_USER_ID = 1


@router.post("", response_model=ScoreResponse, status_code=201)
def create_score(body: ScoreRequest, db: Session = Depends(get_db)):
    ride = db.query(Ride).filter(Ride.id == body.ride_id).first()
    if not ride:
        raise HTTPException(status_code=404, detail="Ride not found")
    if not ride.finished_at:
        raise HTTPException(status_code=400, detail="Ride not finished yet")
    if not ride.actual_coordinates:
        raise HTTPException(status_code=400, detail="Ride has no coordinates")

    # Prevent duplicate scoring
    existing = db.query(Score).filter(Score.ride_id == body.ride_id).first()
    if existing:
        return existing

    bp = db.query(Blueprint).filter(Blueprint.id == ride.blueprint_id).first()
    if not bp:
        raise HTTPException(status_code=404, detail="Blueprint not found")

    result = compute_score(bp.coordinates, ride.actual_coordinates)

    score = Score(
        ride_id=ride.id,
        blueprint_id=ride.blueprint_id,
        user_id=ride.user_id,
        score=result["score"],
        dtw_distance=result["dtw_distance"],
        details=result["details"],
    )
    db.add(score)
    db.commit()
    db.refresh(score)
    return score


@router.get("/{ride_id}", response_model=ScoreResponse)
def get_score(ride_id: int, db: Session = Depends(get_db)):
    score = db.query(Score).filter(Score.ride_id == ride_id).first()
    if not score:
        raise HTTPException(status_code=404, detail="Score not found")
    return score


@router.get("/ranking/{blueprint_id}", response_model=List[RankingEntry])
def get_ranking(blueprint_id: int, db: Session = Depends(get_db)):
    bp = db.query(Blueprint).filter(Blueprint.id == blueprint_id).first()
    if not bp:
        raise HTTPException(status_code=404, detail="Blueprint not found")

    scores = (
        db.query(Score)
        .filter(Score.blueprint_id == blueprint_id)
        .order_by(Score.score.desc())
        .limit(100)
        .all()
    )

    return [
        RankingEntry(
            rank=i + 1,
            user_id=s.user_id,
            ride_id=s.ride_id,
            score=s.score,
            created_at=s.created_at,
        )
        for i, s in enumerate(scores)
    ]
