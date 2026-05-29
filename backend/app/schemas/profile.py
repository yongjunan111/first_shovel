from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ProfileResponse(BaseModel):
    id: int
    email: str
    nickname: str
    profile_image: Optional[str]
    provider: str
    created_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class ProfileUpdate(BaseModel):
    nickname: Optional[str] = Field(default=None, min_length=1, max_length=50)
    profile_image: Optional[str] = Field(default=None, max_length=500)

    model_config = ConfigDict(extra="forbid")
