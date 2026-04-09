from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class RideCreate(BaseModel):
    blueprint_id: int
    started_at: datetime


class RideFinish(BaseModel):
    actual_coordinates: List[List[float]]
    finished_at: datetime
    distance: float
    duration: int  # seconds


class RideResponse(BaseModel):
    id: int
    user_id: int
    blueprint_id: int
    actual_coordinates: Optional[List[List[float]]]
    started_at: datetime
    finished_at: Optional[datetime]
    distance: Optional[float]
    duration: Optional[int]

    class Config:
        from_attributes = True
