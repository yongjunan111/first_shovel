from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship

from app.core.database import Base


class Ride(Base):
    __tablename__ = "rides"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    blueprint_id = Column(Integer, ForeignKey("blueprints.id"), nullable=False)
    # actual_coordinates: [[lat, lng], ...] JSON 저장
    actual_coordinates = Column(JSON)
    started_at = Column(DateTime(timezone=True), nullable=False)
    finished_at = Column(DateTime(timezone=True))
    distance = Column(Float)    # 실제 이동 거리 (km)
    duration = Column(Integer)  # 소요 시간 (초)

    user = relationship("User", back_populates="rides")
    blueprint = relationship("Blueprint", back_populates="rides")
    score = relationship("Score", back_populates="ride", uselist=False)
