# Data Specification

## 데이터 소스

### 고용24 Open API

국민내일배움카드 훈련과정 조회

---

## 수집 방식

현재

API

↓

CSV

↓

Power BI

향후

API

↓

SQLite

↓

Power BI

---

## 수집 주기

현재

월 단위 CSV 수집 및 수동 갱신

목표

daily rolling refresh

```text
현재월 기준 과거 12개월 ~ 미래 6개월
```

Manual full refresh는 필요 시에만 수행한다.

---

## 주요 컬럼

| 컬럼 | 설명 |
|--------|------|
| TRPR_ID | 훈련과정ID |
| TRPR_DEGR | 훈련과정 회차 |
| INST_CD | 기관코드 |
| NCS_CD | NCS코드 |
| TRA_START_DATE | 훈련시작일 |

---

## PK 후보

검증 필요

후보

```text
source_api
TRPR_ID
TRPR_DEGR
TRAINST_CST_ID
TRA_START_DATE
TRA_END_DATE
```

2024 yearly 비교 기준으로는 위 후보가 중복 없이 동작했다.
전체 월간/연간 CSV 대상 추가 검증이 필요하다.

---

## 데이터 적재 방식

1차 방향

- SQLite current table은 최신값만 유지한다.
- 동일 row identity가 없으면 insert한다.
- 동일 row identity가 있고 row_hash가 다르면 update한다.
- 동일 row identity가 있고 row_hash가 같으면 last_seen_at만 갱신한다.
- 상세 old/new value history는 1차 구현에서 제외한다.
- 대신 `row_change_event`에 변경 발생 row와 변경 컬럼 목록을 기록한다.

핵심 테이블 후보:

```text
raw_current_<api>
etl_run_log
row_change_event
```

---

## TODO

- 실제 CSV 컬럼 분석
- PK 검증
- 중복 검증
- NULL 검증
- row_hash 대상 컬럼 확정
- row_change_event 컬럼 확정
