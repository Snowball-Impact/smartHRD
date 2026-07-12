# SmartHRD CSV Warehouse Data Platform

## 프로젝트 소개

SmartHRD는 직업훈련 시장 데이터를 수집·분석하여 Power BI 대시보드로 제공하는 데이터 분석 서비스입니다.

이번 Demo 버전의 목표는 SQLite나 Cloud DW가 아니라, 기존 CSV 기반 운영을 **자동 운영되는 CSV Warehouse 데이터 플랫폼**으로 안정화하는 것입니다.

---

## 현재 구조

```text
고용24 API
-> CSV
-> Power BI Desktop
```

## Demo 목표 구조

```text
Windows Task Scheduler
-> Python ETL
-> Validation
-> CSV Warehouse
-> On-premises Data Gateway
-> Power BI Service / Fabric scheduled refresh
-> SmartHRD Dashboard
```

Power BI는 분석과 시각화만 담당합니다.
데이터 생성, 검증, 교체, 로그 기록은 Python ETL이 담당합니다.

---

## Demo 범위

포함:

- Python 기반 ETL
- 고용24 API 자동 수집
- CSV Warehouse 관리
- Validation
- ETL Logging
- Windows Task Scheduler 실행 스크립트
- Power BI Gateway / Fabric 예약 새로고침 운영 문서

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

## CSV Warehouse 정책

CSV는 임시 산출물이 아니라 Demo 버전의 Warehouse 저장소입니다.

```text
warehouse/
  current/
    training_course.csv
  backup/
  logs/
    etl_log.csv
    api_collection_runs.csv
  tmp/
```

Power BI는 `warehouse/current` 폴더만 읽습니다.

Validation 실패 시 `warehouse/current/training_course.csv`는 절대 덮어쓰지 않습니다.

---

## 업데이트 정책

- 실행 주기: 매주 토요일 새벽
- 기본 수집 범위: 현재월 기준 과거 6개월 ~ 미래 6개월
- 수집 범위는 `--months-back`, `--months-forward` 인자로 변경 가능
- 방식: 매주 전체 범위를 다시 수집한 뒤 current CSV를 교체
- 증분 업데이트: Demo에서는 구현하지 않음

---

## 주요 스크립트

| 파일 | 역할 |
| --- | --- |
| `script/csv_warehouse_etl.py` | CSV Warehouse Demo ETL 진입점 |
| `script/run_csv_warehouse_etl.bat` | Windows Task Scheduler 실행용 배치 파일 |
| `script/monthly_api_collection.py` | 월간 API 수집 CLI |
| `script/work24_collector/` | API 호출, checkpoint, CSV 저장 모듈 |
| `script/yearly_csv_merge.py` | 기존 Power BI 호환용 yearly CSV 병합 |

Demo ETL 실행:

```powershell
python script\csv_warehouse_etl.py --api all --months-back 6 --months-forward 6 --workers 2 --progress-every-pages 10
```

Windows Scheduler에는 다음 파일을 등록합니다.

```text
script\run_csv_warehouse_etl.bat
```

Scheduler에서 기간을 바꾸려면 배치 파일 인자에 ETL 옵션을 추가합니다.

```text
script\run_csv_warehouse_etl.bat --months-back 3 --months-forward 9
```

---

## 반드시 먼저 읽을 문서

1. `README.md`
2. `AGENTS.md`
3. `BACKLOG.md`
4. `docs/PRD.md`
5. `docs/DATA_SPEC.md`
6. `docs/ARCHITECTURE.md`
7. `docs/IMPLEMENTATION_PLAN.md`
8. `docs/CSV_WAREHOUSE_PLATFORM.md`
