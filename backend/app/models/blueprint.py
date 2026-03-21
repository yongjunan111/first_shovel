from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class Blueprint(Base):
    __tablename__ = "blueprints"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(100), nullable=False)
    description = Column(Text)
    tags = Column(JSON, default=list)           # ["산", "도심", ...]
    difficulty = Column(Integer, default=1)     # 1: 쉬움, 2: 보통, 3: 어려움
    estimated_time = Column(Integer)            # 예상 소요 시간 (분)
    distance = Column(Float)                    # 총 거리 (km)
    # coordinates: [[lat, lng], ...] JSON 저장 (PostGIS 마이그레이션 대비)
    coordinates = Column(JSON, nullable=False)
    thumbnail_url = Column(String(500))
    download_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="blueprints")
    rides = relationship("Ride", back_populates="blueprint")
    scores = relationship("Score", back_populates="blueprint")
