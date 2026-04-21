# 기능 요구사항

## 1. Create (블루프린트 생성)

**목적:** 사용자가 GPS 경로를 블루프린트로 업로드/공유  
**담당:** 파트너

### 기능 상세

| 기능 | 설명 | 우선순위 |
|------|------|----------|
| GPX 파일 업로드 | GPX/TCX 파일 파싱 → 좌표 추출 | P0 |
| 경로 미리보기 | 업로드된 경로 지도 시각화 | P0 |
| 메타데이터 입력 | 제목, 설명, 태그, 난이도, 예상 소요시간 | P0 |
| 블루프린트 목록 | 검색/필터/정렬 | P0 |
| 썸네일 자동 생성 | 경로 형태 이미지 캡처 | P1 |
| 인기 블루프린트 | 다운로드 수, 평점 기반 랭킹 | P1 |

### API 엔드포인트

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/blueprints` | 블루프린트 생성 (메타데이터) |
| POST | `/api/blueprints/upload` | GPX 파일 업로드 + 파싱 → 좌표 추출 → PostGIS 저장 |
| GET | `/api/blueprints` | 목록 조회 (필터/페이징/정렬) |
| GET | `/api/blueprints/{id}` | 상세 조회 (좌표 데이터 포함) |
| DELETE | `/api/blueprints/{id}` | 블루프린트 삭제 |

### 요청/응답 스키마

```
POST /api/blueprints/upload
  Request: multipart/form-data { file: GPX, title, description, tags[], difficulty, estimated_time }
  Response: { id, title, coordinates: [[lat, lng], ...], distance, estimated_time }

GET /api/blueprints?tag=animal&difficulty=3&sort=popular&page=1&size=20
  Response: { items: [...], total, page, size }

GET /api/blueprints/{id}
  Response: { id, title, description, tags, difficulty, estimated_time, distance,
              coordinates: [[lat, lng], ...], thumbnail_url, download_count,
              user: { id, nickname }, created_at }
```

---

## 2. Play (Magic Stencil)

**목적:** 블루프린트를 내 위치에 맞게 변환 → 경로 편집 → 실시간 따라가기  
**담당:** 준용

### 기능 상세

| 기능 | 설명 | 우선순위 |
|------|------|----------|
| 좌표 변환 | 시작점 이동 (평행이동 + 회전 + 스케일) | P0 |
| 변환 미리보기 | 변환된 경로가 실제 도로와 맞는지 지도에서 확인 | P0 |
| **경로 편집 (웨이포인트 드래그)** | **변환된 경로의 주요 포인트를 드래그하여 도로에 맞게 수정** | **P1** |
| 실시간 위치 추적 | 라이딩/러닝 중 현재 위치 + 블루프린트 오버레이 | P0 |
| 기록 저장 | 실제 이동 경로 저장 | P0 |
| 경로 이탈 알림 | 블루프린트에서 벗어났을 때 알림 | P2 |

### 경로 편집기 상세 (P1)

사용자가 변환된 블루프린트를 실제 도로에 맞게 수동 조정하는 기능.
자동 Map Matching이 아닌 **사용자 주도 편집** 방식.

> **MVP 대안:** 경로 편집기 미구현 시, 변환 미리보기에서 사용자가 육안으로 도로 적합성 판단 후 라이딩 시작. 편집기는 MVP 이후 우선 추가 대상.

**동작 흐름:**
1. 좌표 변환 후 경로를 지도에 표시
2. 경로의 주요 포인트 10~20개를 드래그 가능한 마커로 표시
3. 사용자가 건물, 강 등 장애물을 확인하고 마커를 드래그하여 도로 위로 이동
4. 마커 이동 시 해당 구간 폴리라인이 실시간 업데이트
5. "포인트 추가" — 폴리라인 위 탭 → 새 웨이포인트 삽입
6. "포인트 삭제" — 마커 길게 눌러 삭제
7. "초기화" — 편집 전 상태로 복원
8. 편집 완료 → 수정된 좌표를 라이딩 목표 경로로 사용

**핵심 원칙:**
- 원본 블루프린트는 변경하지 않음
- 변환 + 편집 결과만 rides.transformed_coordinates에 저장
- 채점은 편집된 경로(transformed) 기준이 아닌 **원본 블루프린트 기준**

### API 엔드포인트

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/stencil/transform` | 좌표 변환 요청 |
| GET | `/api/stencil/preview/{blueprint_id}` | 변환 미리보기 (쿼리 파라미터로 변환 옵션) |
| POST | `/api/rides` | 라이딩 시작 (ride 생성) |
| PUT | `/api/rides/{id}/finish` | 라이딩 종료 (실제 좌표 + 메타데이터 전송) |
| GET | `/api/rides` | 내 라이딩 목록 |
| GET | `/api/rides/{id}` | 라이딩 상세 (좌표 데이터 포함) |

### 요청/응답 스키마

```
POST /api/stencil/transform
  Request: { blueprint_id, target_lat, target_lng, rotation_angle, scale }
  Response: { transformed_coordinates: [[lat, lng], ...], bounds, center, distance }

GET /api/stencil/preview/{blueprint_id}?lat=37.5&lng=127.0&angle=45&scale=1.0
  Response: { transformed_coordinates: [[lat, lng], ...], bounds, center }

POST /api/rides
  Request: { blueprint_id, transformed_coordinates: [[lat, lng], ...] }
  Response: { id, blueprint_id, status: "in_progress", started_at }

PUT /api/rides/{id}/finish
  Request: { actual_coordinates: [[lat, lng], ...], distance, duration }
  Response: { id, status: "completed", finished_at, distance, duration }
```

### 기술 구현 포인트

- **좌표 변환:** Affine Transformation (평행이동, 회전, 스케일링)
- **경로 편집:** Flutter 지도 위 드래그 가능 마커 + 폴리라인 실시간 업데이트
- **실시간 추적:** `geolocator.getPositionStream()` + distanceFilter 5m (OS 레벨)
- **배터리 최적화:** distanceFilter로 불필요한 이벤트 감소, 정지 시 스트림 일시 중단
- **노이즈 필터링:** 직전 좌표 대비 2m 미만 이동 무시 (앱 레벨 추가 필터)

---

## 3. Score (유사도 채점)

**목적:** 원본 블루프린트와 실제 경로의 유사도 점수화  
**담당:** 준용

### 기능 상세

| 기능 | 설명 | 우선순위 |
|------|------|----------|
| 유사도 계산 | DTW 알고리즘으로 경로 유사도 측정 | P0 |
| 점수 시각화 | 0-100점 + 원본/실제 오버레이 비교 | P0 |
| 기본 통계 | 총 거리, 소요 시간, 완주율, 최대 이탈 거리 | P0 |
| 구간별 분석 | 이탈 구간 하이라이트 | P1 |
| 리더보드 | 블루프린트별 최고 점수 랭킹 | P1 |
| 결과 공유 | SNS 공유용 이미지 생성 | P2 |

### API 엔드포인트

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/scores` | 채점 요청 (ride_id 기반) |
| GET | `/api/scores/{ride_id}` | 점수 조회 |
| GET | `/api/scores/ranking/{blueprint_id}` | 블루프린트별 랭킹 (P1) |

### 요청/응답 스키마

```
POST /api/scores
  Request: { ride_id }
  Response: { 
    id, score, dtw_distance, 
    details: { 
      completion_rate,    -- 완주율 (0.0~1.0)
      max_deviation,      -- 최대 이탈 거리 (meters)
      avg_error,          -- 평균 오차 (meters)
      original_points,    -- 원본 좌표 개수
      actual_points       -- 실제 좌표 개수
    },
    created_at 
  }

GET /api/scores/{ride_id}
  Response: (위와 동일)

GET /api/scores/ranking/{blueprint_id}?limit=10
  Response: { items: [{ user: { nickname }, score, created_at }, ...] }
```

### 채점 기준

| 평균 오차 | 점수 범위 | 등급 |
|-----------|-----------|------|
| 0~5m | 85~100점 | 금 (Gold) |
| 5~20m | 50~85점 | 은 (Silver) |
| 20m+ | 0~50점 | 동 (Bronze) |

### 알고리즘

| 알고리즘 | 용도 | 구현 |
|----------|------|------|
| **DTW (fastdtw)** | 메인 유사도 점수 | P0 — `fastdtw` 라이브러리 |
| **Hausdorff** | 최대 이탈 거리 보조 | P0 — details.max_deviation |
| **Douglas-Peucker** | 좌표 다운샘플링 (성능) | P0 — 1000+ 포인트 경로 대응 |
| Frechet | 기하학적 유사도 보조 | P2 — 후순위 |

---

## 4. 공통 기능

**담당:** 파트너

### 인증/회원 관리

| 기능 | 설명 | 우선순위 |
|------|------|----------|
| 소셜 로그인 | Google, Kakao OAuth 2.0 → JWT | P0 |
| 프로필 관리 | 닉네임, 프로필 이미지, 활동 통계 | P1 |
| 내 활동 기록 | 업로드 블루프린트, 완료 라이딩 목록 | P0 |

### API 엔드포인트

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/login` | 소셜 로그인 (OAuth code → JWT) |
| POST | `/api/auth/refresh` | JWT 토큰 갱신 |
| GET | `/api/auth/me` | 현재 사용자 정보 |
| PATCH | `/api/users/me` | 프로필 수정 |
| GET | `/api/users/me/blueprints` | 내 블루프린트 목록 |
| GET | `/api/users/me/rides` | 내 라이드 기록 |

---

## 5. 화면 흐름 (Screen Flow)

```
[로그인] → [홈 (블루프린트 목록)]
                ├── [블루프린트 상세] → [좌표 변환] → [경로 편집 (P1)] → [실시간 추적] → [채점 결과]
                ├── [GPX 업로드]
                └── [내 프로필 / 활동 기록]
```

### 화면별 핵심 요소

| 화면 | 핵심 UI 요소 | 담당 |
|------|-------------|------|
| 로그인 | Google/Kakao 소셜 로그인 버튼 | 파트너 |
| 홈 | 블루프린트 카드 리스트, 검색바, 태그 필터 | 파트너 |
| 블루프린트 상세 | 지도에 경로 표시, 메타데이터, "Play" 버튼 | 파트너 |
| 좌표 변환 | 지도 + 시작점 지정 + 회전/스케일 슬라이더 | 준용 |
| 경로 편집 | 지도 + 드래그 마커 + 포인트 추가/삭제 + 초기화 | 준용 |
| 실시간 추적 | 지도 + 블루프린트 오버레이(파랑) + 내 경로(빨강) + HUD | 준용 |
| 채점 결과 | 점수(큰 숫자) + 오버레이 비교 + 통계 + "다시 도전" | 준용 |
| GPX 업로드 | 파일 선택 + 메타데이터 폼 + 미리보기 | 파트너 |
| 프로필 | 내 블루프린트/라이딩 목록 | 파트너 |

---

> **[2026-04-21 각주]** 위 요구사항의 `POST /api/blueprints/upload` PostGIS 저장 전제는 원문 그대로 보존한다.
> 2주 MVP에서는 좌표를 JSON 컬럼으로 유지하며(결정 A), PostGIS 전환은 post-MVP TODO로 이연한다.
> 구현 시점의 계약은 first-shovel-catchup 룸 결정 A/B를 우선한다.
