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
-> Yearly merge
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
  logs/
    etl_log.csv
    api_collection_runs.csv
    data_snapshot_log.csv
  checkpoints/

dataset/
  work24/
    monthly/
      <API명>/
        <API명>_YYYYMM.csv
    yearly/
      <API명>/
        <API명>_YYYY.csv
```

Power BI는 기존 모델 호환을 위해 `dataset/work24/yearly`를 읽는다.

`dataset/work24/monthly`, `warehouse/checkpoints`, `warehouse/logs`는 Power BI 주 데이터 원본으로 사용하지 않는다.

---

## 수집 정책

정기 수집:

```text
매주 토요일 새벽
현재월 기준 과거 N개월 ~ 미래 N개월
```

Demo에서는 매주 전체 수집 후 yearly CSV를 재생성한다.

증분 업데이트는 구현하지 않는다.

기본값은 과거 6개월, 미래 6개월이며 `--months-back`, `--months-forward` 인자로 변경한다.

---

## ETL 단계

```text
Extract
-> Validate
-> Yearly merge
-> Logging
```

### Extract

고용24 API를 월 단위로 수집한다.

### Validate

- API 호출 성공 여부
- 월별 CSV 저장 성공 여부
- checkpoint 기반 완료/재개 가능 여부
- API expected_count 힌트와 actual_count 차이 warning 기록
- CSV 저장 성공 여부

### Yearly merge

월별 수집이 성공하면 Power BI가 읽는 연도별 CSV를 다시 병합한다.

```text
dataset/work24/monthly
-> dataset/work24/yearly
```

수집 또는 병합 실패 시:

```text
기존 yearly CSV 유지
```

### Logging

모든 ETL 결과를 `warehouse/logs/etl_log.csv`에 기록한다.

yearly CSV 파일별 row count, file size, checksum, 변경 여부는 `warehouse/logs/data_snapshot_log.csv`에 기록한다.

ETL 종료 후 30일이 지난 checkpoint 파일은 cleanup 단계에서 삭제한다.

---

## Power BI 운영

Power BI Desktop은 `dataset/work24/yearly`를 데이터 원본으로 사용한다.

Power BI Service는 On-premises Data Gateway를 통해 예약 새로고침만 수행한다.

PBIX 자동 Publish는 Demo 범위에서 제외한다.
