from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    nickname = Column(String(50), nullable=False)
    profile_image = Column(String(500))
    provider = Column(String(20), nullable=False, default="local")  # google, kakao, local
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    rides = relationship("Ride", back_populates="user")
    blueprints = relationship("Blueprint", back_populates="user")
    scores = relationship("Score", back_populates="user")
