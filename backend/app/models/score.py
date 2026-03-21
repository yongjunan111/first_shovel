from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class Score(Base):
    __tablename__ = "scores"

    id = Column(Integer, primary_key=True, index=True)
    ride_id = Column(Integer, ForeignKey("rides.id"), nullable=False, unique=True)
    blueprint_id = Column(Integer, ForeignKey("blueprints.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    score = Column(Float, nullable=False)           # 0 ~ 100
    dtw_distance = Column(Float, nullable=False)    # 원시 DTW 거리값
    # details: { completion_rate, max_deviation, segment_scores }
    details = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    ride = relationship("Ride", back_populates="score")
    blueprint = relationship("Blueprint", back_populates="scores")
    user = relationship("User", back_populates="scores")
