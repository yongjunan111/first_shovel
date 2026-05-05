from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class BlueprintUser(BaseModel):
    id: int
    nickname: str

    model_config = ConfigDict(from_attributes=True)


class BlueprintCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    difficulty: int = Field(1, ge=1, le=3)
    estimated_time: Optional[int] = Field(default=None, ge=0)
    distance: Optional[float] = Field(default=None, ge=0)
    coordinates: List[List[float]]
    thumbnail_url: Optional[str] = Field(default=None, max_length=500)

    @field_validator("tags")
    @classmethod
    def _clean_tags(cls, tags: List[str]) -> List[str]:
        cleaned: List[str] = []
        for tag in tags:
            value = tag.strip()
            if value and value not in cleaned:
                cleaned.append(value)
        return cleaned

    @field_validator("coordinates")
    @classmethod
    def _validate_coordinates(cls, coordinates: List[List[float]]) -> List[List[float]]:
        if len(coordinates) < 2:
            raise ValueError("coordinates must have at least 2 points")

        normalized: List[List[float]] = []
        for point in coordinates:
            if len(point) != 2:
                raise ValueError("each coordinate must be [lat, lng]")
            try:
                lat = float(point[0])
                lng = float(point[1])
            except (TypeError, ValueError) as exc:
                raise ValueError("coordinates must contain numeric lat/lng values") from exc
            if not (-90 <= lat <= 90):
                raise ValueError("latitude must be between -90 and 90")
            if not (-180 <= lng <= 180):
                raise ValueError("longitude must be between -180 and 180")
            normalized.append([lat, lng])
        return normalized


class BlueprintResponse(BaseModel):
    id: int
    user_id: int
    title: str
    description: Optional[str]
    tags: List[str]
    difficulty: int
    estimated_time: Optional[int]
    distance: Optional[float]
    coordinates: List[List[float]]
    thumbnail_url: Optional[str]
    download_count: int
    created_at: Optional[datetime]
    user: BlueprintUser

    model_config = ConfigDict(from_attributes=True)


class BlueprintListResponse(BaseModel):
    items: List[BlueprintResponse]
    total: int
    page: int
    size: int
