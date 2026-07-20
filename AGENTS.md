# SmartHRD Agent Instructions

## 프로젝트 목적

SmartHRD Demo 버전은 CSV Warehouse 기반 자동 데이터 파이프라인을 구축한다.

Power BI는 분석과 시각화만 담당한다.
데이터 생성, 검증, 교체, 로그 기록은 Python ETL이 담당한다.

---

## 반드시 먼저 읽기

1. README.md
2. BACKLOG.md
3. docs/PRD.md
4. docs/DATA_SPEC.md
5. docs/ARCHITECTURE.md
6. docs/IMPLEMENTATION_PLAN.md
7. docs/CSV_WAREHOUSE_PLATFORM.md

---

## 개발 원칙

### 1. 기존 Power BI 결과를 변경하지 않는다.

기존 대시보드와 동일한 결과를 유지해야 한다.

### 2. CSV Warehouse 구조를 유지한다.

Demo 버전에서는 SQLite, PostgreSQL, Cloud DW를 구현하지 않는다.

### 3. API 원본 데이터는 보존한다.

API 응답 컬럼은 수집/warehouse 계층에서 임의로 삭제하거나 수정하지 않는다.

### 4. ETL 순서

```text
Extract
-> Validate
-> Publish
-> Logging
```

### 5. API Key

절대 코드에 작성하지 않는다.

`.env`를 사용한다.

### 6. CSV 교체

Validation 실패 시 기존 `dataset/work24/yearly` CSV를 유지한다.

절대 실패 산출물로 yearly CSV를 덮어쓰지 않는다.

### 7. 로그

모든 ETL 실행 결과는 CSV 로그로 기록한다.

- run_id
- started_at
- finished_at
- dataset
- status
- expected_count
- actual_count
- duration_seconds
- message

---

## 구현 순서

1. 현재 수집 스크립트 분석
2. 수집 스크립트 리팩토링
3. Validation 추가
4. ETL Logging 추가
5. CSV Warehouse 구조 정리
6. Windows Scheduler 실행 스크립트 작성
7. Power BI Gateway 운영 문서 작성
8. Power BI 운영 현황 Dashboard 설계
