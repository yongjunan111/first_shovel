# 🚴 RideQuest

자전거 라이더를 위한 위치 기반 퀘스트 & 수집 서비스

## 📌 프로젝트 소개

특정 스팟에 도착하면 퀘스트가 해금되고, 완료한 퀘스트를 도감에서 수집하는 게이미피케이션 라이딩 앱입니다.

### 핵심 기능
- 🗺️ **위치 퀘스트**: 특정 장소 도착 시 퀘스트 해금
- 📚 **도감**: 완료한 퀘스트 수집
- 🏃 **활동 기록**: 거리, 시간, 속도, 경로 기록
- ⏱️ **페이스메이커**: 목표 속도 설정 + 실시간 비교
- 🏆 **티어/배지**: 달성 기반 등급 시스템

## 🛠️ 기술 스택

### Backend
- FastAPI
- PostgreSQL (개발: SQLite)
- SQLAlchemy
- JWT 인증

### Frontend
- React (Vite)
- PWA
- 카카오맵 API

## 🚀 시작하기

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
uvicorn main:app --reload
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

## 📁 프로젝트 구조
```
first_shovel/
├── backend/
│   ├── main.py           # FastAPI 앱
│   ├── database.py       # DB 설정
│   ├── models.py         # SQLAlchemy 모델
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   └── package.json
└── README.md
```

## 👥 팀원
- Person A: 인증, GPS 트래킹, 페이스메이커, 히스토리
- Person B: 퀘스트, 도감, 티어/배지, 스팟 데이터

## 🗓️ 로드맵
- [x] Phase 1: PWA (현재)
- [ ] Phase 2: React Native 앱
- [ ] Phase 3: Apple Watch 연동 → 러닝 확장
