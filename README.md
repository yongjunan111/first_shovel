# 🎨 Earth Canvas

GPS 경로를 캔버스 삼아 그림을 그리는 라이딩 채점 서비스

## 📌 프로젝트 소개

도시 지도를 도화지처럼 쓴다. 사용자는 미리 디자인된 그림(블루프린트)을 따라 자전거로 주행하고, 서버는 실제 주행 경로와 블루프린트를 DTW(Dynamic Time Warping)로 비교해 점수를 매긴다.

### 핵심 기능
- 🗂️ **블루프린트(Blueprint)**: GPS 좌표로 표현된 그림 원본. 업로드 · 조회 · 필터링
- 🧭 **스텐실 플레이(Stencil Play)**: 블루프린트를 현재 위치 기준으로 변환해 주행 타겟을 제공
- 🎯 **DTW 스코어링(Score)**: 주행 경로와 타겟 경로를 비교해 점수와 상세 매칭 결과 산출
- 🏆 **랭킹**: 블루프린트별 · 유저별 스코어 랭킹

## 🛠️ 기술 스택

### Backend
- FastAPI
- PostgreSQL + SQLAlchemy + Alembic
- JWT 인증
- fastdtw + numpy (경로 스코어링)

### Frontend
- Flutter
- flutter_map + CyclOSM 타일 (지도 렌더링)

## 🚀 시작하기

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
uvicorn main:app --reload
```

### Frontend
```bash
cd frontend
flutter pub get
flutter run
```

## 📁 프로젝트 구조
```
first_shovel/
├── backend/
│   ├── main.py              # FastAPI 엔트리포인트
│   ├── app/
│   │   ├── core/            # 설정, DB, 에러 핸들러
│   │   ├── models/          # SQLAlchemy 모델 (User, Blueprint, Ride, Score)
│   │   ├── routers/         # stencil, rides, scores
│   │   └── services/        # 좌표 변환, DTW 스코어링
│   ├── alembic/             # 마이그레이션
│   ├── tests/
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── lib/                 # Flutter 소스
│   └── pubspec.yaml
└── README.md
```

## 👥 팀원
- 파트너: Play/Score 백엔드, Flutter scaffold
- 준용: Auth/Profile/Create API, Score 기준 경로 계약, Flutter Play UI

## 🗓️ 로드맵
- [ ] Phase 1 (MVP): Blueprint CRUD + Stencil Play + DTW Score + 랭킹 + Flutter Play UI
- [ ] Phase 2: 소셜/공유 기능, 이벤트 블루프린트
- [ ] Phase 3: PostGIS 전환 + 공간 쿼리 최적화
