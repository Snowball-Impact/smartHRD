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
- 월별 CSV 수집 후 yearly CSV와 Power BI용 integrated CSV 재생성

산출물:

```text
script/csv_warehouse_etl.py
script/csv_warehouse/
```

---

## Step 3. CSV Warehouse 구조 정리

- `warehouse/logs`
- `warehouse/checkpoints`
- `dataset/work24/monthly`
- `dataset/work24/yearly`
- `dataset/work24/integrated`

Power BI는 `dataset/work24/integrated`를 조회한다.

---

## Step 4. Validation 추가

검증 항목:

- API 호출 성공 여부
- 월별 CSV 저장 성공 여부
- checkpoint 기반 완료/재개 가능 여부
- API expected_count 힌트와 actual_count 차이 warning 기록
- yearly CSV 병합 성공 여부
- integrated CSV 병합 성공 여부
- CSV 저장 성공 여부

Validation 실패 시 기존 yearly/integrated CSV는 유지한다.

---

## Step 5. ETL Logging 추가

로그 파일:

```text
warehouse/logs/etl_log.csv
warehouse/logs/data_snapshot_log.csv
```

컬럼:

```text
run_id
started_at
finished_at
status
expected_count
actual_count
duration_seconds
message
```

`data_snapshot_log.csv`는 integrated CSV 파일별 checksum, 이전 checksum, row_count, file_size_bytes, is_changed를 기록한다.

ETL cleanup은 30일이 지난 `warehouse/checkpoints/*.json` 파일을 삭제한다.

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

- Power BI Desktop 원본 경로를 `dataset/work24/integrated`로 설정
- On-premises Data Gateway에 동일 경로 등록
- Power BI Service에서 예약 새로고침 설정
- PBIX 자동 Publish는 제외

---

## Step 8. Power BI 운영 현황 Dashboard 설계

`warehouse/logs/etl_log.csv`를 Power BI로 읽어 운영 현황 페이지를 구성한다.

추천 지표:

- 최근 실행 상태
- 최근 성공 시각
- 최근 데이터 변경 여부
- 변경된 integrated 파일 수
- expected_count vs actual_count
- duration_seconds 추이
- 실패 메시지
