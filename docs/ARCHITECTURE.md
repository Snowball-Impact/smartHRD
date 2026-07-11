# Architecture

## 현재 구조

API

↓

CSV

↓

Power BI

---

## 목표 구조

Windows Scheduler

↓

run_etl.py

↓

Extract

↓

Validate

↓

Transform

↓

SQLite

↓

Power BI

↓

Fabric

---

## 수집 정책

정기 수집은 daily rolling refresh 하나만 둔다.

```text
현재월 기준 과거 12개월
↓
현재월 기준 미래 6개월
```

예시 기준일 2026-07-11:

```text
2025-07-01 ~ 2027-01-31
```

weekly/monthly 스케줄은 daily rolling refresh와 겹치므로 제거한다.

Manual full refresh는 API 변경, 데이터 품질 검증, 과거 재검증이 필요할 때만 수행한다.

---

## DB 구조

raw

↓

staging

↓

dimension

↓

fact

↓

mart

---

## 초기 SQLite 테이블 방향

1차 SQLite 구현은 dimension/fact 모델링보다 raw/current 안정화를 우선한다.

초기 후보:

```text
raw_current_<api>
etl_run_log
row_change_event
```

`raw_current_<api>`는 최신값만 유지한다.

`row_change_event`는 전체 old/new 값을 저장하지 않고, 변경 발생 row와 변경 컬럼 목록만 기록한다.

자세한 업데이트 전략은 `docs/DW_UPDATE_STRATEGY.md`를 따른다.

---

## ETL

Extract

↓

Validate

↓

Transform

↓

Load

---

## Power BI

SQLite를 직접 조회한다.

Power BI는 데이터를 저장하지 않는다.
