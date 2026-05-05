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

## 📐 API 계약 메모

### `POST /api/rides` — Ride 시작

필수 필드: `blueprint_id`, `started_at`.

스텐실 파라미터(`target_lat`, `target_lng`, `rotation_angle`, `scale`)는 모두 **optional**이다.

- `target_lat` + `target_lng` 둘 다 전달하면 서버가 `transform_coordinates`로 스텐실 변환 결과를 계산해 `target_coordinates`로 저장한다 (`rotation_angle` 기본 0, `scale` 기본 1.0).
- 둘 다 생략하면 서버가 `blueprint.coordinates`를 그대로 `target_coordinates`로 저장한다 (변환 없음, 원본 경로로 채점).
- 한쪽(`target_lat` 또는 `target_lng`)만 전달하면 `422 VALIDATION_ERROR`로 거부된다.
- `target_coordinates`를 요청 바디로 직접 보내도 서버가 무시한다. 기준 경로는 반드시 서버가 계산·저장한다.

채점(`POST /api/scores`)은 `ride.target_coordinates` ↔ `ride.actual_coordinates`만 비교한다. 런타임에 `blueprint.coordinates`로 fallback하지 않는다.

### `GET /api/scores/ranking/{blueprint_id}` — 블루프린트별 랭킹

**공개 엔드포인트.** 인증이 필요 없다. 리더보드는 비로그인 사용자에게도 노출되며, 응답에는 상위 100건의 `rank / user_id / ride_id / score / created_at`이 포함된다. 점수 생성/조회(`POST /api/scores`, `GET /api/scores/{ride_id}`)는 계속 인증이 필요하다(소유자만).

### `POST /api/auth/dev-login` — 로컬 개발 전용 토큰 발급

**로컬 개발 전용 엔드포인트다. 운영에서는 반드시 비활성 상태를 유지한다.**

- `settings.ALLOW_DEV_LOGIN`의 기본값은 **False**(`backend/app/core/config.py`). 환경변수 미설정 시 자동으로 비활성화되어 401을 반환한다.
- 로컬 개발에서는 `.env`에 `ALLOW_DEV_LOGIN=true`를 두어 opt-in한다 (`backend/.env.example` 참고).
- 운영 배포 전 `.env`에서 해당 줄을 제거하거나 `false`로 돌려놓는다.
- 테스트에서는 `monkeypatch.setattr(app.core.config.settings, "ALLOW_DEV_LOGIN", True)`로 명시적으로 열어서 사용한다.

### `GET /api/auth/{provider}/authorize` · `/callback` — OAuth (scaffold-only)

⚠️ **현재 OAuth 플로우는 scaffold 단계이며 운영 배포 금지.** 이유:

- CSRF `state` 값을 `backend/app/routers/auth.py`의 **in-process set**(`_PENDING_STATES`)에 보관한다. 프로세스가 재시작되면 pending state가 전부 날아가고, 멀티워커(uvicorn --workers >1, gunicorn) 환경에서는 워커 간 공유가 안 되어 정상 사용자도 state mismatch로 401을 맞는다.
- 즉, 현재 구현은 **단일 워커 로컬 개발 전용**이다. 운영 배포 전 state 저장소를 Redis/DB/서명된 쿠키 중 하나로 교체해야 한다.
- `authorize`는 `state` 파라미터를 항상 포함하며, `callback`은 누락/불일치/재사용(single-use)된 state에 대해 Day 4 포맷(`{detail, error_code: "UNAUTHORIZED"}`)으로 401을 반환한다.
- 프로바이더(`_exchange_and_fetch_google/kakao`)의 `httpx.TimeoutException`/`httpx.HTTPError`/`ValueError(JSON)`은 전부 `UnauthorizedError`로 변환되어 동일한 에러 envelope로 나간다.

### JWT 시크릿 환경변수

- 정식 이름은 `JWT_SECRET_KEY`. 레거시 `SECRET_KEY`도 alias로 읽는다(`JWT_SECRET_KEY` 우선, 미설정 시 `SECRET_KEY` 사용).
- `ENV=production`에서 유효 시크릿이 placeholder(`change-me-in-production`)로 남아 있으면 설정 로딩 단계에서 `ValueError`로 기동이 실패한다. dev/test 환경은 placeholder 허용.

## 👥 팀원
- 파트너: Play/Score 백엔드, Flutter scaffold
- 준용: Auth/Profile/Create API, Score 기준 경로 계약, Flutter Play UI

## 🗓️ 로드맵
- [ ] Phase 1 (MVP): Blueprint CRUD + Stencil Play + DTW Score + 랭킹 + Flutter Play UI
- [ ] Phase 2: 소셜/공유 기능, 이벤트 블루프린트
- [ ] Phase 3: PostGIS 전환 + 공간 쿼리 최적화
