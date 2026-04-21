from pydantic import BaseModel, ConfigDict, Field, model_validator
from typing import List, Optional
from datetime import datetime


class RideCreate(BaseModel):
    blueprint_id: int
    started_at: datetime
    # Stencil transform parameters — all optional.
    # If both target_lat and target_lng are omitted, the server uses
    # blueprint.coordinates as target_coordinates (no transform).
    # If only one of the pair is supplied, the request is rejected (422).
    # Client cannot pass target_coordinates directly (integrity guard).
    target_lat: Optional[float] = Field(default=None, ge=-90, le=90)
    target_lng: Optional[float] = Field(default=None, ge=-180, le=180)
    rotation_angle: float = 0.0
    scale: float = Field(1.0, gt=0)

    @model_validator(mode="after")
    def _target_lat_lng_paired(self) -> "RideCreate":
        if (self.target_lat is None) != (self.target_lng is None):
            raise ValueError(
                "target_lat and target_lng must be provided together "
                "(both present for a stencil transform, or both omitted to reuse blueprint.coordinates)"
            )
        return self


class RideFinish(BaseModel):
    actual_coordinates: List[List[float]]
    finished_at: datetime
    distance: float
    duration: int  # seconds


class RideResponse(BaseModel):
    id: int
    user_id: int
    blueprint_id: int
    target_coordinates: List[List[float]]
    actual_coordinates: Optional[List[List[float]]]
    started_at: datetime
    finished_at: Optional[datetime]
    distance: Optional[float]
    duration: Optional[int]

    model_config = ConfigDict(from_attributes=True)
