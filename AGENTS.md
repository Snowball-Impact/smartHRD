# SmartHRD Agent Instructions

## 프로젝트 목적

CSV 기반 Power BI 모델을 SQLite 기반 Data Warehouse로 전환한다.

Power BI는 시각화만 담당한다.

---

## 반드시 먼저 읽기

1. docs/PRD.md
2. docs/DATA_SPEC.md
3. docs/ARCHITECTURE.md
4. docs/IMPLEMENTATION_PLAN.md

---

## 개발 원칙

### 1. 기존 Power BI 결과를 변경하지 않는다.

기존 대시보드와 동일한 결과를 유지해야 한다.

---

### 2. API 원본 데이터는 보존한다.

API 응답 컬럼은 raw 계층에서 삭제하거나 수정하지 않는다.

---

### 3. ETL은 다음 순서를 따른다.

Extract

↓

Validate

↓

Transform

↓

Load

---

### 4. API Key

절대 코드에 작성하지 않는다.

.env 사용.

---

### 5. DB 적재

SQLite를 사용한다.

CSV는 Export 용도로만 사용한다.

---

### 6. 로그

모든 ETL 실행 결과는 기록한다.

- 시작시간
- 종료시간
- 성공여부
- 수집건수
- 오류메시지

---

## 구현 순서

1. 데이터 분석
2. SQLite 구축
3. ETL 구현
4. Power BI 연결
5. 자동화
