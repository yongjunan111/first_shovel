# Earth Canvas — 2주 MVP 상세 태스크 플랜

> **전제:** Claude Code + Codex 바이브코딩 | 하루 4시간 | 주 6일 (월~토)  
> **총 작업일:** 12일 (48시간)  
> **준용:** Play (Magic Stencil) + Score (DTW 채점)  
> **파트너:** Create (블루프린트) + 공통 (OAuth, 프로필)  
> **전략:** Week 1 백엔드 올킬 → Week 2 Flutter UI + 통합 + 배포

---

## 핵심 마일스톤

| 시점 | 기준 | 상태 |
|------|------|------|
| **Day 2 끝** | DB 스키마 확정 + FastAPI 라우터 뼈대 | 🏗️ 기반 완성 |
| **Day 4 끝** | Play/Score 백엔드 API 전체 Swagger 통과 | ⭐ **핵심 체크포인트** |
| **Day 6 끝** | 파트너 Create API도 완성 → 백엔드 올킬 | 🎯 Week 1 목표 |
| **Day 9 끝** | Play 화면 동작 (변환 → 지도 표시 → 추적 → 저장) | 📱 코어 UI |
| **Day 11 끝** | Create → Play → Score 전체 플로우 E2E | 🔗 통합 완료 |
| **Day 12 끝** | 배포 + 시드 데이터 + 데모 가능 | 🚀 MVP 완성 |

---

## Week 1 — 환경 세팅 + 백엔드 올킬 (Day 1~6)

### Day 1 (월) — 프로젝트 세팅 + DB 설계 [공통]

**준용 (4시간)**
- [ ] GitHub 모노레포 생성 (`backend/` + `frontend/`)
  - [ ] `.gitignore`, 브랜치 전략 (main/develop/feature/*) 세팅
  - [ ] PR 템플릿 작성
- [ ] Docker Compose로 PostgreSQL + PostGIS 컨테이너 구성
  - [ ] `docker-compose.yml` 작성 (postgres:16 + postgis)
  - [ ] DB 접속 확인 + `CREATE EXTENSION postgis;`
- [ ] FastAPI 프로젝트 초기 세팅
  - [ ] 폴더 구조: `app/` → `routers/`, `models/`, `schemas/`, `services/`, `core/`
  - [ ] CORS 미들웨어, 환경변수 관리 (`pydantic-settings`)
  - [ ] SQLAlchemy + GeoAlchemy2 설정
  - [ ] health check 엔드포인트 (`GET /health`)
- [ ] DB 스키마 설계 (파트너와 합의)
  - [ ] `users`: id, email, nickname, profile_image, provider, created_at
  - [ ] `blueprints`: id, user_id, title, description, tags[], difficulty, estimated_time, distance, coordinates(LINESTRING), thumbnail_url, download_count, created_at
  - [ ] `rides`: id, user_id, blueprint_id, transformed_coordinates(LINESTRING), actual_coordinates(LINESTRING), started_at, finished_at, distance, duration, status
  - [ ] `scores`: id, ride_id, blueprint_id, user_id, score, dtw_distance, details(JSON), created_at
  - [ ] Alembic 마이그레이션 초기화 + 테이블 생성

**파트너 (4시간)**
- [ ] Flutter 프로젝트 생성 + 기본 세팅
  - [ ] 상태관리 (Provider) 구조 잡기
  - [ ] 폴더 구조: `screens/`, `widgets/`, `services/`, `models/`
  - [ ] API 클라이언트 베이스 (`dio` 패키지)
- [ ] OAuth 2.0 플로우 설계 (Google, Kakao)
  - [ ] FastAPI 인증 라우터 뼈대 생성
  - [ ] JWT 토큰 발급/검증 로직

---

### Day 2 (화) — Play 백엔드 API 개발 [준용 핵심]

**준용 (4시간)**
- [ ] 좌표 변환 서비스 구현 (`services/stencil.py`)
  - [ ] Affine Transform: 평행이동 (시작점 → 사용자 지정 위치)
  - [ ] 회전 (각도 파라미터)
  - [ ] 스케일링 (축소/확대)
  - [ ] 단위 테스트 3개 이상 (이동만, 회전+이동, 전체 변환)
- [ ] 좌표 변환 API 엔드포인트
  - [ ] `POST /api/stencil/transform`
    - Request: `{ blueprint_id, target_lat, target_lng, rotation_angle, scale }`
    - Response: `{ transformed_coordinates: [[lat, lng], ...], bounds, center }`
  - [ ] `GET /api/stencil/preview/{blueprint_id}?lat=&lng=&angle=&scale=`
    - 미리보기용 경량 응답
- [ ] rides CRUD API
  - [ ] `POST /api/rides` — 라이딩 시작 (blueprint_id, transformed_coordinates, started_at)
  - [ ] `PUT /api/rides/{id}/finish` — 라이딩 종료 (actual_coordinates, finished_at, distance, duration)
  - [ ] `GET /api/rides` — 내 라이딩 목록
  - [ ] `GET /api/rides/{id}` — 라이딩 상세 (좌표 데이터 포함)

**파트너 (4시간)**
- [ ] OAuth 인증 구현 (Google/Kakao → JWT)
- [ ] 유저 CRUD API (프로필 조회/수정)
- [ ] GPX 파싱 서비스 구현 (`gpxpy` 활용)

---

### Day 3 (수) — Score 백엔드 API 개발 [준용 핵심]

**준용 (4시간)**
- [ ] DTW 유사도 서비스 구현 (`services/scoring.py`)
  - [ ] `fastdtw` 라이브러리 활용 기본 구현
  - [ ] 좌표 정규화 (위도/경도 → 미터 단위 변환 후 비교)
  - [ ] 점수 산출 로직: DTW distance → 0~100점 변환
    - 정규화 기준: 경로 길이 대비 평균 이탈 거리
    - 보너스/페널티: 완주율, 최대 이탈 거리
  - [ ] 단위 테스트 (동일 경로=100점, 완전 다른 경로=낮은 점수, 약간 이탈=80~90점)
- [ ] Score API 엔드포인트
  - [ ] `POST /api/scores` — 채점 요청
    - Request: `{ ride_id }`
    - 내부: ride의 actual_coordinates vs blueprint의 coordinates DTW 비교
    - Response: `{ score, dtw_distance, details: { completion_rate, max_deviation, avg_error, original_points, actual_points } }`
  - [ ] `GET /api/scores/{ride_id}` — 점수 조회
  - [ ] `GET /api/scores/ranking/{blueprint_id}` — 블루프린트별 랭킹 (P1이지만 쿼리 간단)
- [ ] 좌표 다운샘플링 유틸리티
  - [ ] 긴 경로(1000+ 포인트) 대응: Douglas-Peucker 알고리즘으로 간소화
  - [ ] 성능 테스트 (5000 포인트 경로 기준 응답시간 < 2초)

**파트너 (4시간)**
- [ ] GPX 업로드 + 파싱 API 완성
  - [ ] `POST /api/blueprints/upload` — GPX 파일 → PostGIS 좌표 저장
- [ ] 블루프린트 CRUD API
  - [ ] `POST /api/blueprints`, `GET /api/blueprints`, `GET /api/blueprints/{id}`
  - [ ] 목록 필터/페이징 (태그, 난이도, 거리 범위)

---

### Day 4 (목) — 백엔드 통합 테스트 + 엣지케이스 [준용]

**준용 (4시간)**
- [ ] Play → Score 통합 테스트
  - [ ] 시나리오: 블루프린트 선택 → 좌표 변환 → 라이딩 저장 → 채점
  - [ ] Swagger UI에서 수동 E2E 테스트
  - [ ] pytest 통합 테스트 작성 (최소 3개 시나리오)
- [ ] 엣지케이스 처리
  - [ ] 좌표 변환: 극단적 스케일 (0.1x ~ 10x) 검증
  - [ ] DTW: 좌표 개수 불일치 처리 (원본 100개 vs 실제 50개)
  - [ ] 빈 좌표 배열, 단일 포인트 경로 등 예외 처리
- [ ] API 에러 응답 표준화
  - [ ] 커스텀 예외 클래스 (NotFound, ValidationError, ...)
  - [ ] 에러 응답 포맷: `{ detail: string, error_code: string }`
- [ ] PostGIS 쿼리 최적화
  - [ ] 좌표 저장/조회 성능 확인
  - [ ] 공간 인덱스 (GiST) 추가

**파트너 (4시간)**
- [ ] Create 백엔드 마무리 + 통합 테스트
- [ ] 인증 미들웨어 연동 (JWT 검증 → 전 API에 적용)

---

### Day 5 (금) — Flutter 기초 + 지도 연동 시작 [준용]

> ⭐ **Day 5 시작 전 체크:** Play/Score 백엔드 API 전체 Swagger 통과 확인! (Day 4까지 완료 목표)  
> 안 됐으면 오전에 백엔드 마무리, 오후에 Flutter 시작.

**준용 (4시간)**
- [ ] Flutter 프로젝트 환경 확인 (파트너가 Day 1에 생성한 프로젝트)
  - [ ] 에뮬레이터 or 실기기 연결 + Hot Reload 확인
  - [ ] 기존 폴더 구조/상태관리 방식 파악
- [ ] 지도 패키지 연동
  - [ ] `flutter_naver_map` 또는 `kakao_map_plugin` 설치 + API 키 등록
  - [ ] 기본 지도 화면 렌더링 확인
  - [ ] 지도 위 폴리라인 그리기 테스트 (하드코딩된 좌표로)
  - [ ] 안 되면 `flutter_map` (OSM/Leaflet) fallback
- [ ] GPS 위치 가져오기
  - [ ] `geolocator` 패키지 설치 + 권한 설정 (Android/iOS)
  - [ ] 현재 위치 가져오기 테스트
  - [ ] 지도에 현재 위치 마커 표시

**파트너 (4시간)**
- [ ] Flutter 로그인 화면 (OAuth 소셜 로그인)
- [ ] 홈 화면 뼈대 (블루프린트 목록 - API 연동)

---

### Day 6 (토) — Play 핵심 화면 개발 [준용]

**준용 (4시간)**
- [ ] 블루프린트 선택 → 좌표 변환 화면
  - [ ] 블루프린트 목록에서 하나 선택 (파트너의 목록 API 활용)
  - [ ] 현재 위치 자동 감지 or 지도에서 시작점 탭하여 지정
  - [ ] 회전/스케일 슬라이더 UI
  - [ ] "변환" 버튼 → `POST /api/stencil/transform` 호출
- [ ] 변환 미리보기 화면
  - [ ] 변환된 경로를 지도 위에 폴리라인으로 표시
  - [ ] 현재 도로/지형과 겹쳐 보여서 "따라갈 수 있는지" 육안 확인 가능
  - [ ] "시작하기" 버튼 → 라이딩 모드 진입

**파트너 (4시간)**
- [ ] GPX 업로드 화면 (파일 선택 + 메타데이터 입력)
- [ ] 블루프린트 상세 화면 (경로 지도 시각화)

---

## Week 2 — Flutter UI 완성 + 통합 + 배포 (Day 7~12)

### Day 7 (월) — 실시간 GPS 추적 화면 [준용 핵심]

**준용 (4시간)**
- [ ] 라이딩 모드 화면 구현
  - [ ] 블루프린트 경로 오버레이 (파란색 폴리라인)
  - [ ] 내 현재 위치 실시간 마커 (GPS 스트리밍)
  - [ ] 실제 이동 경로 실시간 그리기 (빨간색 폴리라인, 점점 늘어남)
  - [ ] 경과 시간, 이동 거리 표시 (상단 HUD)
- [ ] GPS 추적 로직
  - [ ] `geolocator.getPositionStream()` 으로 위치 스트리밍
  - [ ] 좌표 배열에 실시간 누적
  - [ ] 샘플링 주기: 이동 시 2초, 정지 시 10초 (적응형)
  - [ ] 노이즈 필터링: 직전 좌표와 거리 < 2m이면 무시
- [ ] 라이딩 시작/종료
  - [ ] "시작" → `POST /api/rides` (ride 생성)
  - [ ] "종료" → `PUT /api/rides/{id}/finish` (좌표 배열 + 메타데이터 전송)
  - [ ] 종료 후 Score 화면으로 자동 이동

**파트너 (4시간)**
- [ ] 내 프로필 / 내 활동 기록 화면
- [ ] 블루프린트 검색/필터 UI

---

### Day 8 (화) — 경로 편집기 (P1 — 시간 부족 시 스킵) [준용]

> Day 7까지 순조로우면 구현. 밀리고 있으면 스킵하고 Day 9 Score 화면으로 넘어가기.
> 스킵 시 변환 미리보기만으로 운영 (사용자가 지도 보고 판단).

**준용 (4시간)**
- [ ] 변환 미리보기 화면에 편집 기능 추가
  - [ ] 블루프린트 경로의 주요 포인트를 드래그 가능한 마커로 표시
    - 전체 포인트 X → 일정 간격으로 10~20개 핵심 포인트만 마커화
  - [ ] 마커 드래그 시 해당 구간의 폴리라인이 실시간 업데이트
  - [ ] "포인트 추가": 폴리라인 위 탭 → 새 웨이포인트 삽입
  - [ ] "포인트 삭제": 마커 길게 눌러 삭제
- [ ] 편집된 경로 저장
  - [ ] 편집 완료 → 수정된 좌표 배열을 새로운 변환 결과로 사용
  - [ ] 원본 블루프린트는 변경하지 않음 (변환+편집 결과만 라이딩에 사용)
- [ ] UI/UX 보완
  - [ ] "초기화" 버튼 (편집 전 상태로 복원)
  - [ ] 편집 전/후 토글 비교

**파트너 (4시간)**
- [ ] Create 플로우 E2E 연결 (업로드 → 파싱 → 목록 → 상세)
- [ ] 전체 네비게이션 구조 정리 (하단 탭바 or Drawer)

---

### Day 9 (수) — Score 결과 화면 + Play 플로우 E2E [준용]

**준용 (4시간)**
- [ ] Score 결과 화면 구현
  - [ ] 0~100점 큰 숫자 표시 (등급별 색상: 90+ 금, 70+ 은, 50+ 동)
  - [ ] 원본 블루프린트(파랑) vs 실제 경로(빨강) 오버레이 지도
  - [ ] 기본 통계: 총 거리, 소요 시간, 완주율
  - [ ] "다시 도전" 버튼 → Play 화면으로
- [ ] Play 전체 플로우 E2E 테스트
  - [ ] 블루프린트 선택 → 변환 미리보기 → (편집) → 추적 시작 → 종료 → 채점 → 결과
  - [ ] 실기기에서 GPS 추적 실제 테스트 (짧은 경로로)
  - [ ] API 호출 실패 시 에러 핸들링 (토스트/스낵바)
- [ ] Score API 연동
  - [ ] 라이딩 종료 후 자동 `POST /api/scores` 호출
  - [ ] 결과 화면에 응답 데이터 바인딩

**파트너 (4시간)**
- [ ] Create → 목록 → 상세 플로우 E2E 테스트
- [ ] 로그인 → 홈 → 각 화면 네비게이션 연결

---

### Day 10 (목) — 전체 통합 + QA [공통]

**준용 (4시간)**
- [ ] Create → Play → Score 전체 통합 테스트
  - [ ] 시나리오 1: 파트너가 업로드한 블루프린트 → 내가 Play → Score
  - [ ] 시나리오 2: 변환 + 편집 후 라이딩 → 채점
  - [ ] 시나리오 3: 같은 블루프린트 여러 번 도전 → 각각 점수 저장
- [ ] 버그 수정 (우선순위: 크래시 > 기능 안 됨 > UI 깨짐)
- [ ] GPS 추적 안정성 보강
  - [ ] 앱 백그라운드 진입 시 GPS 유지 확인
  - [ ] GPS 끊김 시 마지막 유효 좌표 유지 + 재연결
- [ ] 로딩 상태 처리
  - [ ] API 호출 중 스피너/프로그레스 표시
  - [ ] 변환 중, 채점 중, 업로드 중 각각 로딩 UI

**파트너 (4시간)**
- [ ] 전체 UI 통일성 정리 (색상, 폰트, 간격)
- [ ] 빈 상태 UI (블루프린트 없을 때, 라이딩 기록 없을 때)
- [ ] 에러 화면 처리 (네트워크 에러, 서버 에러)

---

### Day 11 (금) — 배포 + 시드 데이터 [공통]

**준용 (4시간)**
- [ ] 백엔드 배포
  - [ ] Railway 또는 Render 계정 세팅
  - [ ] 환경 변수 설정 (DATABASE_URL, JWT_SECRET, CORS_ORIGINS)
  - [ ] 배포 + health check 통과 확인
  - [ ] HTTPS 동작 확인
- [ ] DB 배포
  - [ ] Supabase 또는 Neon 셋업 (PostGIS 지원 확인!)
  - [ ] Alembic 마이그레이션 실행
  - [ ] 테이블 생성 + PostGIS extension 확인
- [ ] 시드 데이터 준비
  - [ ] 데모용 블루프린트 2~3개 (실제 GPX 파일)
    - 간단한 거 1개 (직선+곡선, 3km 이내)
    - 복잡한 거 1개 (동물/문자 형태, 5km+)
  - [ ] 테스트 유저 계정 생성
  - [ ] 데모용 라이딩 기록 + 점수 1~2개

**파트너 (4시간)**
- [ ] Flutter 빌드 (APK 또는 Web)
- [ ] 배포된 백엔드로 API base URL 전환 + CORS 확인
- [ ] 빌드 에러 수정

---

### Day 12 (토) — 최종 점검 + 데모 준비 [공통]

**준용 (4시간)**
- [ ] 배포 환경 E2E 최종 테스트
  - [ ] 실기기에서 배포된 앱으로 전체 플로우 1회 통과
  - [ ] 크리티컬 버그 핫픽스
- [ ] README 작성
  - [ ] 프로젝트 소개 (Earth Canvas 한 줄 설명)
  - [ ] 기술 스택 + 아키텍처 다이어그램
  - [ ] 주요 기능 스크린샷/GIF
  - [ ] 로컬 실행 방법 (backend + frontend)
  - [ ] API 문서 링크 (Swagger URL)
- [ ] 데모 시나리오 리허설
  - [ ] "블루프린트 업로드 → 검색 → 선택 → 변환 → 편집 → 추적 → 채점" 전체 흐름
  - [ ] 예상 질문 대비 (DTW 알고리즘, 좌표 변환 원리)
- [ ] 코드 정리
  - [ ] 불필요한 print/log 제거
  - [ ] 주석 정리
  - [ ] develop → main 머지

**파트너 (4시간)**
- [ ] 발표 자료 준비 (데모 시나리오 포함)
- [ ] 최종 UI 스크린샷 캡처
- [ ] 최종 버그 수정

---

## 일별 시간 배분 가이드

| Day | 준용 주요 작업 | 시간 배분 |
|-----|---------------|-----------|
| 1 | 세팅 + DB 설계 | 세팅 2h + DB 2h |
| 2 | Play API (변환 + rides) | 변환 로직 2.5h + API 1.5h |
| 3 | Score API (DTW + 채점) | DTW 구현 2.5h + API 1.5h |
| 4 | 통합 테스트 + 엣지케이스 | 테스트 2h + 예외처리 2h |
| 5 | Flutter + 지도 연동 | 환경 1h + 지도 2h + GPS 1h |
| 6 | Play 화면 (변환 + 미리보기) | 변환 UI 2.5h + 미리보기 1.5h |
| 7 | 실시간 GPS 추적 화면 | 추적 로직 2.5h + UI 1.5h |
| 8 | 경로 편집기 | 드래그 마커 2.5h + 저장 1.5h |
| 9 | Score 화면 + E2E | Score UI 2h + E2E 2h |
| 10 | 전체 통합 QA | 버그 수정 3h + 안정화 1h |
| 11 | 배포 + 시드 데이터 | 배포 2.5h + 시드 1.5h |
| 12 | 최종 점검 + 문서 | README 2h + 데모 1h + 정리 1h |

---

## 리스크 시나리오별 대응

### 🔴 Day 4 끝났는데 백엔드 API 안 끝남
→ Day 5 오전까지 백엔드 마무리, Flutter 시작을 Day 5 오후로 밀기  
→ 경로 편집기(Day 8) 드랍하고 "변환 미리보기만" 으로 축소

### 🟡 Day 6 끝났는데 지도 패키지 안 됨
→ `flutter_naver_map` 포기 → `flutter_map` (OSM 타일) 즉시 전환  
→ flutter_map은 셋업이 더 쉬우니까 반나절이면 복구

### 🔴 Day 9 끝났는데 GPS 추적이 불안정
→ 실시간 추적 포기 → "라이딩 후 GPX 파일 업로드" 방식으로 전환  
→ Score만 살리면 MVP 가치는 유지됨

### 🟡 Day 11 배포에서 삽질
→ Railway 안 되면 Render, Render도 안 되면 로컬 서버 + ngrok  
→ DB는 Supabase 안 되면 Neon, 둘 다 안 되면 Railway PostgreSQL 애드온

---

## P0 (반드시) vs 드랍 가능 정리

| 반드시 구현 (P0) | 시간 부족 시 축소 | 드랍 (P2) |
|-------------------|-------------------|-----------|
| GPX 업로드 + 파싱 | **경로 편집기 → "보기만" 으로 (P1)** | 경로 이탈 알림 |
| 좌표 변환 (평행이동+회전+스케일) | 실시간 추적 → GPX 업로드 방식 | SNS 공유 이미지 |
| 실시간 GPS 추적 | 랭킹 → 개인 점수만 | 구간별 분석 |
| DTW 유사도 채점 | 프로필 → 로그인만 | 썸네일 자동 생성 |
| 점수 시각화 (오버레이 비교) | | 인기 블루프린트 |
| OAuth 로그인 | | |

---

## 바이브코딩 활용 가이드

### Claude Code 활용 포인트
- **FastAPI + PostGIS 백엔드 전체** → 스캐폴딩 + 비즈니스 로직 생성
- **DTW 알고리즘 구현** → 코드 생성 후 테스트 케이스로 검증
- **Flutter 위젯 생성** → 화면 단위로 "이런 화면 만들어줘" + 리뷰
- **에러 디버깅** → 에러 메시지 붙여넣기 → 즉시 수정안

### Codex 활용 포인트 (파트너)
- **OAuth 구현** → 보일러플레이트 코드 생성
- **Flutter UI 컴포넌트** → 리스트, 폼, 카드 등
- **GPX 파싱 로직** → gpxpy 활용 코드

### 주의사항
- AI가 생성한 코드는 **반드시 이해하고 리뷰** → 블랙박스 금지
- PostGIS 쿼리는 **실제 데이터로 테스트** 필수 (AI가 문법 틀릴 수 있음)
- Flutter 패키지 버전 호환성 → AI가 옛날 버전 코드 줄 수 있으니 공식 문서 교차 확인

---

> **[2026-04-21 각주]** 위 원문의 PostGIS 전제는 당시 계획의 기록으로 보존한다.
> 2주 MVP 범위에서는 좌표를 JSON 컬럼으로 유지하고(결정 A), PostGIS 전환은 post-MVP TODO로 이연한다.
> 관련 결정은 first-shovel-catchup 룸의 결정 A/B 참조.
