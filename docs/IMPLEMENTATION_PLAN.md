# Implementation Plan

## Step 1. 현재 수집 스크립트 분석

- `script/monthly_api_collection.py` 분석
- `script/work24_collector/` 모듈 분석
- API key `.env` 관리 확인
- checkpoint/resume 구조 확인
- 기존 monthly/yearly CSV 구조 확인

상태: 완료

---

## Step 2. 수집 스크립트 리팩토링

- 기존 collector 모듈 재사용
- Demo 운영용 진입점 추가
- 매주 수집 window 자동 계산
- 전체 수집 결과를 CSV Warehouse tmp 파일로 병합

산출물:

```text
script/csv_warehouse_etl.py
```

---

## Step 3. CSV Warehouse 구조 정리

- `warehouse/current`
- `warehouse/backup`
- `warehouse/logs`
- `warehouse/tmp`

Power BI는 `warehouse/current`만 조회한다.

---

## Step 4. Validation 추가

검증 항목:

- API 호출 성공 여부
- 예상 건수 == 실제 건수
- 필수 컬럼 존재 여부
- 필수 컬럼 NULL/빈값 여부
- row identity 중복 여부
- CSV 저장 성공 여부

Validation 실패 시 기존 current CSV는 유지한다.

---

## Step 5. ETL Logging 추가

로그 파일:

```text
warehouse/logs/etl_log.csv
```

컬럼:

```text
run_id
started_at
finished_at
dataset
status
expected_count
actual_count
duration_seconds
message
```

---

## Step 6. Windows Scheduler 실행 스크립트 작성

산출물:

```text
script/run_csv_warehouse_etl.bat
```

권장 스케줄:

```text
매주 토요일 새벽
```

---

## Step 7. Power BI Gateway 운영 문서 작성

- Power BI Desktop 원본 경로를 `warehouse/current/training_course.csv`로 설정
- On-premises Data Gateway에 동일 경로 등록
- Power BI Service에서 예약 새로고침 설정
- PBIX 자동 Publish는 제외

---

## Step 8. Power BI 운영 현황 Dashboard 설계

`warehouse/logs/etl_log.csv`를 Power BI로 읽어 운영 현황 페이지를 구성한다.

추천 지표:

- 최근 실행 상태
- 최근 성공 시각
- expected_count vs actual_count
- duration_seconds 추이
- 실패 메시지

