# SmartHRD Data Warehouse PRD

## 프로젝트 목적

현재 SmartHRD는 CSV 기반으로 데이터를 관리하고 있다.

데이터 수집 주기가 월 단위이며,
Power BI가 데이터 저장과 분석 역할을 동시에 수행하고 있다.

SQLite 기반 Data Warehouse를 구축하여
데이터 저장과 분석을 분리한다.

---

## 문제점

- CSV 파일 증가
- 수동 업데이트
- 최신 데이터 반영 어려움
- Power BI 모델 복잡도 증가
- 데이터 재사용 어려움

---

## 목표

### 기능

- API 자동 수집
- SQLite 저장
- Power BI 연결
- Fabric 새로고침 지원

---

## 범위

포함

- 고용24 API
- SQLite
- ETL
- Power BI

제외

- Cloud DW
- 웹서비스
- AI Agent

---

## 성공 기준

- ETL 자동 실행 가능
- CSV 제거
- Power BI 동일 결과
- SQLite를 단일 데이터 저장소로 사용
