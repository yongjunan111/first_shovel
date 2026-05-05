from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.exceptions import NotFoundError, BadRequestError
from app.models.score import Score
from app.models.ride import Ride
from app.models.blueprint import Blueprint
from app.models.user import User
from app.schemas.score import ScoreRequest, ScoreResponse, RankingEntry
from app.services.scoring import compute_score

router = APIRouter(prefix="/api/scores", tags=["scores"])


@router.post("", response_model=ScoreResponse, status_code=201)
def create_score(
    body: ScoreRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ride = db.query(Ride).filter(Ride.id == body.ride_id).first()
    if not ride:
        raise NotFoundError(f"Ride {body.ride_id} not found")
    # Ownership: a ride can only be scored by its owner — cross-user hidden as 404.
    if ride.user_id != current_user.id:
        raise NotFoundError(f"Ride {body.ride_id} not found")
    if not ride.finished_at:
        raise BadRequestError("Ride not finished yet")
    if not ride.actual_coordinates or len(ride.actual_coordinates) < 2:
        raise BadRequestError("Ride has insufficient coordinates for scoring")
    if not ride.target_coordinates or len(ride.target_coordinates) < 2:
        raise BadRequestError("Ride has insufficient target coordinates for scoring")

    # Prevent duplicate scoring — return existing
    existing = db.query(Score).filter(Score.ride_id == body.ride_id).first()
    if existing:
        return existing

    result = compute_score(ride.target_coordinates, ride.actual_coordinates)

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


@router.get("/ranking/{blueprint_id}", response_model=List[RankingEntry])
def get_ranking(
    blueprint_id: int,
    db: Session = Depends(get_db),
):
    # Ranking is intentionally public — no get_current_user dependency. See README.

    if not db.query(Blueprint).filter(Blueprint.id == blueprint_id).first():
        raise NotFoundError(f"Blueprint {blueprint_id} not found")

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


@router.get("/{ride_id}", response_model=ScoreResponse)
def get_score(
    ride_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    score = db.query(Score).filter(Score.ride_id == ride_id).first()
    if not score:
        raise NotFoundError(f"Score for ride {ride_id} not found")
    # Ownership check: a user may only view their own score.
    if score.user_id != current_user.id:
        raise NotFoundError(f"Score for ride {ride_id} not found")
    return score
