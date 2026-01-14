from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    nickname = Column(String(50), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # 관계
    rides = relationship("Ride", back_populates="user")
    completed_quests = relationship("CompletedQuest", back_populates="user")


class Spot(Base):
    """퀘스트가 발생하는 위치"""
    __tablename__ = "spots"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    radius = Column(Integer, default=100)  # 인식 반경 (미터)
    
    # 관계
    quests = relationship("Quest", back_populates="spot")


class Quest(Base):
    """퀘스트"""
    __tablename__ = "quests"

    id = Column(Integer, primary_key=True, index=True)
    spot_id = Column(Integer, ForeignKey("spots.id"), nullable=False)
    title = Column(String(100), nullable=False)
    description = Column(Text)
    difficulty = Column(Integer, default=1)  # 1: 쉬움, 2: 보통, 3: 어려움
    points = Column(Integer, default=10)
    
    # 관계
    spot = relationship("Spot", back_populates="quests")
    completions = relationship("CompletedQuest", back_populates="quest")


class CompletedQuest(Base):
    """완료한 퀘스트 (도감)"""
    __tablename__ = "completed_quests"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    quest_id = Column(Integer, ForeignKey("quests.id"), nullable=False)
    completed_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # 관계
    user = relationship("User", back_populates="completed_quests")
    quest = relationship("Quest", back_populates="completions")


class Ride(Base):
    """라이딩 기록"""
    __tablename__ = "rides"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=False)
    ended_at = Column(DateTime(timezone=True))
    distance = Column(Float)  # km
    duration = Column(Integer)  # 초
    avg_speed = Column(Float)  # km/h
    route_data = Column(Text)  # JSON으로 GPS 좌표 저장
    
    # 관계
    user = relationship("User", back_populates="rides")
