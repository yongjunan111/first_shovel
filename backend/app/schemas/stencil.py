from pydantic import BaseModel, Field
from typing import List


class StencilTransformRequest(BaseModel):
    blueprint_id: int
    target_lat: float = Field(..., ge=-90, le=90)
    target_lng: float = Field(..., ge=-180, le=180)
    rotation_angle: float = Field(0.0, description="Clockwise degrees")
    scale: float = Field(1.0, gt=0)


class Bounds(BaseModel):
    min_lat: float
    max_lat: float
    min_lng: float
    max_lng: float


class Center(BaseModel):
    lat: float
    lng: float


class StencilTransformResponse(BaseModel):
    transformed_coordinates: List[List[float]]
    bounds: Bounds
    center: Center
