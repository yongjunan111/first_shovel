from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List
import math

from database import get_db
import models
import schemas

router = APIRouter(prefix="/spots", tags=["spots"])


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    두 좌표 사이의 거리를 계산 (km)
    Haversine 공식 사용
    """
    R = 6371  # 지구 반경 (km)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    return R * 2 * math.asin(math.sqrt(a))


@router.get("/", response_model=schemas.SpotList)
def get_spots(db: Session = Depends(get_db)):
    """전체 스팟 목록 조회"""
    spots = db.query(models.Spot).all()
    return {"total": len(spots), "spots": spots}


@router.get("/nearby", response_model=schemas.SpotList)
def get_nearby_spots(
    lat: float = Query(..., description="현재 위도"),
    lon: float = Query(..., description="현재 경도"),
    radius_km: float = Query(default=5.0, description="검색 반경 (km)"),
    db: Session = Depends(get_db),
):
    """
    현재 위치 기준 근처 스팟 검색
    Haversine 공식으로 거리 계산
    """
    all_spots = db.query(models.Spot).all()
    nearby = [
        s
        for s in all_spots
        if haversine(lat, lon, s.latitude, s.longitude) <= radius_km
    ]
    return {"total": len(nearby), "spots": nearby}


@router.get("/{spot_id}", response_model=schemas.Spot)
def get_spot(spot_id: int, db: Session = Depends(get_db)):
    """스팟 상세 조회"""
    spot = db.query(models.Spot).filter(models.Spot.id == spot_id).first()
    if not spot:
        raise HTTPException(status_code=404, detail="Spot not found")
    return spot
