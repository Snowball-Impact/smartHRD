# CSV Warehouse Platform

## 목적

SmartHRD Demo 버전은 CSV를 Warehouse 저장소로 사용한다.

Python ETL은 고용24 API 데이터를 수집하고, 검증이 통과한 경우에만 Power BI가 읽는 current CSV를 교체한다.

---

## 실행 명령

수동 실행:

```powershell
python script\csv_warehouse_etl.py --api all --months-back 6 --months-forward 6 --workers 2 --progress-every-pages 10
```

Windows Task Scheduler 실행 파일:

```text
script\run_csv_warehouse_etl.bat
```

---

## Refresh Window

기본값:

```text
현재월 기준 과거 N개월 ~ 미래 N개월
```

예시:

```powershell
python script\csv_warehouse_etl.py --as-of 20260712 --months-back 6 --months-forward 6
```

수집 범위:

```text
2026-01-01 ~ 2027-01-31
```

기간 인자는 운영 시 변경할 수 있다.

```powershell
python script\csv_warehouse_etl.py --api all --months-back 3 --months-forward 9
```

Windows Task Scheduler에서 배치 파일을 쓸 때도 ETL 인자를 그대로 넘길 수 있다.

```text
script\run_csv_warehouse_etl.bat --months-back 3 --months-forward 9
```

---

## Publish 정책

ETL은 먼저 run별 tmp 디렉터리에 데이터를 생성한다.

```text
warehouse/tmp/<run_id>/training_course.tmp.csv
```

Validation 통과 시:

```text
warehouse/current/training_course.csv
-> warehouse/backup/training_course_<run_id>.csv

warehouse/tmp/<run_id>/training_course.tmp.csv
-> warehouse/current/training_course.csv
```

Validation 실패 시:

```text
warehouse/current/training_course.csv 유지
```

---

## Validation

현재 Demo Validator:

- API 수집 중 예외 발생 여부
- expected_count와 actual_count 일치 여부
- 필수 컬럼 존재 여부
- 필수 컬럼 NULL/빈값 여부
- row identity 중복 여부
- tmp CSV 생성 여부

필수 컬럼:

```text
trprId
trprDegr
trainstCstId
traStartDate
traEndDate
```

중복 기준:

```text
source_api
trprId
trprDegr
trainstCstId
traStartDate
traEndDate
```

TODO:

- 실제 전체 API 결과에서 필수 컬럼 NULL 정책 검증
- Power BI 모델에서 `source_api`, `source_dataset`, `source_period` 추가 컬럼 영향 검증

---

## ETL 로그

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

Power BI 운영 현황 페이지는 이 로그를 읽는다.

---

## Power BI Gateway 운영

Power BI Desktop:

- 데이터 원본을 `warehouse/current/training_course.csv`로 설정한다.
- tmp, backup, monthly 폴더는 원본으로 사용하지 않는다.

Power BI Service:

- On-premises Data Gateway에서 같은 파일 경로를 등록한다.
- 예약 새로고침만 설정한다.
- PBIX 자동 Publish는 Demo 범위에서 제외한다.

운영 권장 순서:

1. 로컬에서 ETL 수동 실행
2. `warehouse/current/training_course.csv` 생성 확인
3. Power BI Desktop에서 current CSV 연결
4. Power BI Service 게시
5. Gateway 데이터 원본 경로 등록
6. 매주 ETL 완료 이후 Power BI 예약 새로고침이 실행되도록 시간 조정
