# CSV Warehouse Platform

## 목적

SmartHRD Demo 버전은 CSV를 Warehouse 저장소로 사용한다.

Python ETL은 고용24 API 데이터를 월별 CSV로 수집하고, 수집이 성공한 경우 yearly CSV와 Power BI가 읽는 integrated CSV를 재생성한다.

---

## 실행 명령

수동 실행:

```powershell
python script\csv_warehouse_etl.py --api all --months-back 6 --months-forward 6 --period-retries 1 --workers 2 --progress-every-pages 10
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

월별 API 수집 중 API 호출 오류가 발생하면 `--period-retries` 횟수만큼 해당 API/월을 처음부터 다시 수집한다.

```powershell
python script\csv_warehouse_etl.py --api all --period-retries 2
```

ETL 전체가 실패한 뒤 같은 명령을 다시 실행하면 기본적으로 `warehouse/checkpoints`의 checkpoint를 기준으로 이어받는다.

기본 실행 모드는 `--run-mode auto`이다.
완료된 checkpoint의 `collection_date`가 실행 기준일보다 7일 이상 오래되면 정기 수집으로 판단해 해당 월을 page 1부터 다시 수집한다.
7일이 지나지 않았다면 장애 복구 실행으로 판단해 이미 완료된 월은 checkpoint 기준으로 skip하고, incomplete 월은 이어받거나 처음부터 다시 수집한다.

정기 수집을 강제하려면 `--run-mode scheduled`를 사용한다.
장애 복구를 강제하려면 `--run-mode resume`을 사용한다.
기존 `--fresh-run`은 `--run-mode scheduled`의 호환 옵션이다.

```powershell
python script\csv_warehouse_etl.py --api all --run-mode scheduled
```

---

## Publish 정책

ETL은 API/월 단위로 monthly CSV를 생성한다.

```text
dataset/work24/monthly/<API명>/<API명>_YYYYMM.csv
```

수집이 성공하면 yearly CSV를 다시 병합한 뒤, Power BI 원본인 API별 integrated CSV를 다시 병합한다.

```text
dataset/work24/monthly/<API명>/<API명>_YYYYMM.csv
-> dataset/work24/yearly/<API명>/<API명>_YYYY.csv
-> dataset/work24/integrated/<API명>/<API명>.csv
```

수집 또는 병합 실패 시:

```text
기존 dataset/work24/yearly, dataset/work24/integrated CSV 유지
```

integrated CSV 교체 후에는 파일별 checksum을 비교해 실제 변경 여부를 로그로 남긴다.

```text
warehouse/logs/data_snapshot_log.csv
```

월별 수집이 모두 skip된 경우에는 yearly/integrated 병합도 skip한다.
병합을 강제로 실행하려면 `--force-publish`를 추가한다.

`integrated` CSV는 API별 파일 단위로 yearly CSV를 합치며, 각 API 원본 컬럼을 그대로 보존한다.

---

## Validation

현재 Demo Validator:

- API 수집 중 예외 발생 여부
- API expected_count 힌트와 actual_count 차이 여부
- 월별 수집 실패 시 설정된 횟수만큼 재시도
- ETL 재실행 시 checkpoint 기반 재개
- 월별 CSV 생성 여부
- yearly CSV 병합 성공 여부
- integrated CSV 병합 성공 여부
- integrated CSV checksum 기반 변경 여부 기록

API의 `scn_cnt`는 수집 건수 힌트로 사용한다.
최종 완료 판정은 페이지를 순회하다가 마지막 페이지가 `page_size`보다 짧아지는 시점으로 판단한다.
`scn_cnt`와 실제 수집 건수가 다르면 FAIL이 아니라 ETL 로그의 warning message로 남긴다.

---

## Cleanup

ETL 종료 후 기본 cleanup을 실행한다.

```text
warehouse/checkpoints/*.json
```

기본 보존 기간은 30일이다.

```powershell
python script\csv_warehouse_etl.py --checkpoint-retention-days 30
```

cleanup을 건너뛰려면 다음 옵션을 사용한다.

```powershell
python script\csv_warehouse_etl.py --skip-cleanup
```

TODO:

- 실제 전체 API 결과에서 nullable 컬럼 정책 검증
- Power BI 모델에서 `source_api`, `source_dataset`, `source_period` 추가 컬럼 영향 검증

---

## ETL 로그

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
window_start
window_end
duration_seconds
message
```

Power BI 운영 현황 페이지는 이 로그를 읽는다.

`data_snapshot_log.csv` 컬럼:

```text
run_id
created_at
dataset
api
year
file_path
row_count
file_size_bytes
checksum
previous_checksum
is_changed
message
```

---

## Power BI Gateway 운영

Power BI Desktop:

- 데이터 원본을 `dataset/work24/integrated`로 설정한다.
- monthly 폴더와 checkpoint/log 폴더는 주 데이터 원본으로 사용하지 않는다.

Power BI Service:

- On-premises Data Gateway에서 같은 파일 경로를 등록한다.
- 예약 새로고침만 설정한다.
- PBIX 자동 Publish는 Demo 범위에서 제외한다.

운영 권장 순서:

1. 로컬에서 ETL 수동 실행
2. `dataset/work24/integrated` CSV 생성 확인
3. Power BI Desktop에서 integrated CSV 연결
4. Power BI Service 게시
5. Gateway 데이터 원본 경로 등록
6. 매주 ETL 완료 이후 Power BI 예약 새로고침이 실행되도록 시간 조정
