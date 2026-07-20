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
-> CSV Warehouse current
-> Power BI Service scheduled refresh
```

---

## 수집 주기

- 매주 토요일 새벽
- 기본값은 현재월 기준 과거 6개월 ~ 미래 6개월
- `--months-back`, `--months-forward` 인자로 수집 범위 변경 가능
- 매주 전체 범위를 다시 수집하여 current CSV를 교체
- 증분 업데이트는 Demo에서 구현하지 않음

예시 기준일 `2026-07-12`:

```text
2026-01-01 ~ 2027-01-31
```

---

## CSV Warehouse 산출물

Power BI 원본:

```text
warehouse/current/training_course.csv
```

실패 방지용 임시 파일:

```text
warehouse/tmp/<run_id>/training_course.tmp.csv
```

기존 current 백업:

```text
warehouse/backup/training_course_<run_id>.csv
```

ETL 로그:

```text
warehouse/logs/etl_log.csv
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
- 예상 건수 == 실제 건수
- 필수 컬럼 존재 여부
- 필수 컬럼 NULL/빈값 검증
- row identity 중복 검증
- CSV 저장 성공 여부

필수 컬럼:

```text
trprId
trprDegr
traStartDate
traEndDate
```

중복 검증 후보:

```text
source_api
trprId
trprDegr
trainstCstId
traStartDate
traEndDate
```

TODO:

- 전체 API/기간에 대한 추가 nullable 컬럼 정책 확정
- Power BI 기존 모델과 추가 메타 컬럼 영향 검증
- 운영 현황 Dashboard용 로그 컬럼 확정
