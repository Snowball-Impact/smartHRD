# Implementation Plan

## Phase 1

기존 시스템 분석

- API 분석
- CSV 분석
- Power BI 분석
- 기존 yearly CSV와 신규 yearly CSV 변경 비교
- daily rolling refresh 정책 결정
- row_hash 기반 upsert 및 change event 전략 결정

---

## Phase 2

Data Warehouse 설계

- SQLite 생성
- 테이블 설계
- ERD 작성
- `raw_current_<api>` 설계
- `etl_run_log` 설계
- `row_change_event` 설계
- row identity key 검증
- row_hash 대상 컬럼 정의

---

## Phase 3

ETL 구현

- API 호출
- SQLite 저장
- 로그 기록
- daily rolling refresh window 계산
- latest-value upsert
- row_hash 비교
- change event 기록
- missing/inactive 후보 처리

---

## Phase 4

Power BI 연결

- SQLite 연결
- 모델 변경
- 검증

---

## Phase 5

자동화

- Windows Scheduler
- ETL 자동 실행
- Fabric Refresh
