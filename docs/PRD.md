# SmartHRD CSV Warehouse PRD

## 프로젝트 목적

현재 SmartHRD는 고용24 API 데이터를 CSV로 수집한 뒤 Power BI에서 직접 읽어 운영한다.

이번 Demo 버전의 목적은 CSV를 제거하는 것이 아니라, CSV를 Warehouse 저장소로 인정하고 자동 수집, 검증, 교체, 로그 기록까지 포함한 운영 가능한 데이터 플랫폼을 구축하는 것이다.

---

## 문제점

- 수동 업데이트
- 최신 데이터 반영 어려움
- 실패한 수집 파일이 Power BI 원본을 덮어쓸 위험
- 수집/검증/발행/로그 단계가 명확히 분리되지 않음
- Power BI Service 예약 새로고침 운영 문서 부족

---

## 목표

- Python ETL 자동 실행
- 고용24 API 자동 수집
- Validation 통과 시에만 Power BI 원본 integrated CSV 재생성
- 실패 시 기존 yearly/integrated CSV 유지
- ETL 로그 CSV 기록
- integrated CSV checksum 기반 실제 데이터 변경 여부 기록
- Windows Task Scheduler 연동
- On-premises Data Gateway 기반 Power BI Service 예약 새로고침 지원

---

## 범위

포함:

- 고용24 API
- CSV Warehouse
- Python ETL
- Validation
- ETL Logging
- Windows Scheduler
- Power BI Gateway / Fabric 예약 새로고침

제외:

- SQLite
- PostgreSQL
- Cloud Data Warehouse
- Airflow
- Docker
- Kubernetes
- AI Agent
- 운영 콘솔

---

## 성공 기준

- 매주 토요일 새벽 ETL 자동 실행 가능
- 과거 6개월 ~ 미래 6개월 범위 자동 수집 가능
- `dataset/work24/integrated`가 Power BI의 안정 원본으로 유지됨
- Validation 실패 시 기존 yearly/integrated CSV가 보존됨
- `warehouse/logs/etl_log.csv`로 운영 현황을 Power BI에서 시각화 가능
- `warehouse/logs/data_snapshot_log.csv`로 integrated CSV 변경 여부를 Power BI에서 시각화 가능
