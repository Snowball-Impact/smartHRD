# Architecture

## 현재 구조

```text
고용24 API
-> CSV
-> Power BI
```

---

## Demo 목표 구조

```text
Windows Task Scheduler
-> script/run_csv_warehouse_etl.bat
-> script/csv_warehouse_etl.py
-> Extract
-> Validate
-> Publish
-> Logging
-> CSV Warehouse
-> On-premises Data Gateway
-> Power BI Service / Fabric scheduled refresh
-> SmartHRD Dashboard
```

---

## CSV Warehouse 구조

```text
warehouse/
  current/
    training_course.csv
  backup/
    training_course_<run_id>.csv
  logs/
    etl_log.csv
    api_collection_runs.csv
  tmp/
    <run_id>/
      monthly/
      checkpoints/
      training_course.tmp.csv
```

Power BI는 `warehouse/current`만 읽는다.

`warehouse/tmp`와 `warehouse/backup`은 Power BI 원본으로 사용하지 않는다.

---

## 수집 정책

정기 수집:

```text
매주 토요일 새벽
현재월 기준 과거 N개월 ~ 미래 N개월
```

Demo에서는 매주 전체 수집 후 current CSV를 교체한다.

증분 업데이트는 구현하지 않는다.

기본값은 과거 6개월, 미래 6개월이며 `--months-back`, `--months-forward` 인자로 변경한다.

---

## ETL 단계

```text
Extract
-> Validate
-> Publish
-> Logging
```

### Extract

고용24 API를 월 단위로 수집한다.

### Validate

- API 호출 성공 여부
- 예상 건수 == 실제 건수
- 중복 검증
- 필수 컬럼 NULL/빈값 검증
- CSV 저장 성공 여부

### Publish

Validation 통과 시:

```text
기존 current CSV 백업
-> tmp CSV를 current CSV로 교체
```

Validation 실패 시:

```text
기존 current CSV 유지
```

### Logging

모든 ETL 결과를 `warehouse/logs/etl_log.csv`에 기록한다.

---

## Power BI 운영

Power BI Desktop은 `warehouse/current/training_course.csv`를 데이터 원본으로 사용한다.

Power BI Service는 On-premises Data Gateway를 통해 예약 새로고침만 수행한다.

PBIX 자동 Publish는 Demo 범위에서 제외한다.
