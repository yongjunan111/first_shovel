from pydantic import BaseModel
from typing import List, Optional


class SpotBase(BaseModel):
    name: str
    description: Optional[str] = None
    latitude: float
    longitude: float
    radius: int = 150


class Spot(SpotBase):
    id: int

    class Config:
        from_attributes = True


class SpotList(BaseModel):
    total: int
    spots: List[Spot]
