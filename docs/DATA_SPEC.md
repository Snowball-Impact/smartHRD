# Data Specification

## 데이터 소스

### 고용24 Open API

훈련과정 목록 API:

| Dataset | Endpoint |
| --- | --- |
| 국민내일배움카드훈련과정 | `310L01` |
| 사업주훈련 | `311L01` |
| 국가인적자원개발 컨소시엄 | `312L01` |
| 일학습병행 | `313L01` |

---

## 수집 방식

현재:

```text
API
-> CSV
-> Power BI
```

Demo 목표:

```text
API
-> Python ETL
-> Validation
-> dataset/work24/monthly
-> dataset/work24/yearly
-> Power BI Service scheduled refresh
```

---

## 수집 주기

- 매주 토요일 새벽
- 기본값은 현재월 기준 과거 6개월 ~ 미래 6개월
- `--months-back`, `--months-forward` 인자로 수집 범위 변경 가능
- 매주 전체 범위를 다시 수집하여 yearly CSV를 재생성
- 증분 업데이트는 Demo에서 구현하지 않음

예시 기준일 `2026-07-12`:

```text
2026-01-01 ~ 2027-01-31
```

---

## CSV Warehouse 산출물

Power BI 원본:

```text
dataset/work24/yearly/
```

월별 수집 파일:

```text
dataset/work24/monthly/<API명>/<API명>_YYYYMM.csv
```

연도별 병합 파일:

```text
dataset/work24/yearly/<API명>/<API명>_YYYY.csv
```

ETL 로그:

```text
warehouse/logs/etl_log.csv
warehouse/logs/api_collection_runs.csv
warehouse/logs/data_snapshot_log.csv
warehouse/checkpoints/*.json
```

주요 ETL 로그 컬럼:

```text
run_id
started_at
finished_at
dataset
status
expected_count
actual_count
window_start
window_end
months_back
months_forward
is_resume
duration_seconds
message
```

데이터 변경 스냅샷 로그 컬럼:

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

## 주요 컬럼

API 원본 컬럼은 보존한다.

Demo ETL은 운영 추적을 위해 다음 메타 컬럼을 앞에 추가한다.

| 컬럼 | 설명 |
| --- | --- |
| `source_api` | API 코드 |
| `source_dataset` | 데이터셋 표시명 |
| `source_period` | 수집 월 |

주요 원본 컬럼:

| 컬럼 | 설명 |
| --- | --- |
| `trprId` | 훈련과정 ID |
| `trprDegr` | 훈련과정 회차 |
| `trainstCstId` | 훈련기관 고객 ID |
| `instCd` | 기관 코드 |
| `ncsCd` | NCS 코드 |
| `traStartDate` | 훈련 시작일 |
| `traEndDate` | 훈련 종료일 |

---

## Validation 항목

- API 호출 성공 여부
- 월별 CSV 저장 성공 여부
- checkpoint 기반 완료/재개 가능 여부
- 연도별 CSV 병합 성공 여부
- API expected_count 힌트와 actual_count 차이 warning 기록
- yearly CSV 파일 checksum 기반 변경 여부 기록
- CSV 저장 성공 여부

TODO:

- 전체 API/기간에 대한 nullable 컬럼 정책 확정
- Power BI 기존 모델과 추가 메타 컬럼 영향 검증
- 운영 현황 Dashboard용 로그 컬럼 확정
