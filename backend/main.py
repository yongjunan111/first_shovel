from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import engine
from routers import spots
import models

# DB 테이블 생성
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="RideQuest API",
    description="자전거 라이더를 위한 위치 기반 퀘스트 서비스",
    version="0.1.0"
)

# CORS 설정 (React 프론트엔드 연동용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(spots.router)


@app.get("/")
def root():
    return {"message": "RideQuest API 서버가 실행 중입니다"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}

