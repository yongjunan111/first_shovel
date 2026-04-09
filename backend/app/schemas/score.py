from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from datetime import datetime


class ScoreRequest(BaseModel):
    ride_id: int


class ScoreDetails(BaseModel):
    completion_rate: float
    avg_deviation_m: float
    max_deviation_m: float
    segment_scores: List[float]
    blueprint_length_m: float
    actual_length_m: float


class ScoreResponse(BaseModel):
    id: int
    ride_id: int
    blueprint_id: int
    user_id: int
    score: float
    dtw_distance: float
    details: ScoreDetails
    created_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class RankingEntry(BaseModel):
    rank: int
    user_id: int
    ride_id: int
    score: float
    created_at: Optional[datetime]
