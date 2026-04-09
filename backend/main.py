from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import Base, engine, SessionLocal
import app.models  # noqa: F401 — 모든 모델 등록 후 테이블 생성
from app.models.user import User
from app.routers import stencil, rides, scores

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Earth Canvas API",
    description="GPS 경로를 캔버스 삼아 그림을 그리는 라이딩 채점 서비스",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(stencil.router)
app.include_router(rides.router)
app.include_router(scores.router)


@app.on_event("startup")
def seed_dev_user() -> None:
    """Ensure a placeholder user (id=1) exists for pre-auth development.
    Remove this once JWT auth lands on Day 4."""
    db = SessionLocal()
    try:
        if not db.query(User).filter(User.id == 1).first():
            db.add(User(email="dev@earthcanvas.local", nickname="DevUser", provider="local"))
            db.commit()
    finally:
        db.close()


@app.get("/", tags=["root"])
def root():
    return {"message": "Earth Canvas API 서버가 실행 중입니다"}


@app.get("/health", tags=["health"])
def health_check():
    return {"status": "healthy", "service": "earth-canvas-api"}
