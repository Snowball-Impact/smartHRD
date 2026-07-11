# SmartHRD Data Warehouse

## 프로젝트 소개

SmartHRD는 직업훈련 시장 데이터를 수집·분석하여 Power BI 대시보드로 제공하는 데이터 분석 서비스입니다.

기존에는 CSV 파일을 데이터 저장소처럼 사용하여 Power BI에서 직접 데이터모델을 구성하였습니다.

본 프로젝트는 CSV 기반 구조를 SQLite 기반 On-Premise Data Warehouse로 전환하여
데이터 수집, 저장, 분석 계층을 분리하는 것을 목표로 합니다.

---

## 현재 구조

API

↓

CSV

↓

Power BI


---

## 목표 구조

고용24 API

↓

Python ETL

↓

SQLite Data Warehouse

↓

Power BI Desktop

↓

Power BI Service / Fabric


---

## 프로젝트 목표

- CSV 의존성 제거
- SQLite 기반 DW 구축
- ETL 자동화
- Power BI는 분석 전용으로 사용
- Fabric 예약 새로고침 지원
- 향후 PostgreSQL 마이그레이션 가능 구조 확보

---

## 문서 현황

다음 컨텍스트에서는 먼저 이 README를 읽고, 아래 순서대로 docs를 파악합니다.

### 다음 컨텍스트 시작 순서

1. `docs/NEXT_CONTEXT_HANDOFF.md`
2. `docs/API_MONTHLY_COLLECTION.md`
3. `docs/REFRESH_POLICY.md`
4. `docs/DW_UPDATE_STRATEGY.md`
5. `docs/YEARLY_CHANGE_ANALYSIS.md`
6. `docs/CURRENT_SYSTEM_ANALYSIS.md`
7. `docs/PRD.md`
8. `docs/DATA_SPEC.md`
9. `docs/ARCHITECTURE.md`
10. `docs/IMPLEMENTATION_PLAN.md`

### 문서별 역할

| 문서 | 역할 |
| --- | --- |
| `docs/NEXT_CONTEXT_HANDOFF.md` | 현재까지 작업 히스토리, 결정사항, 다음 작업 인수인계 |
| `docs/API_MONTHLY_COLLECTION.md` | 월간 API 수집 스크립트, 병렬 수집, checkpoint, yearly merge 사용법 |
| `docs/REFRESH_POLICY.md` | daily rolling refresh와 manual full refresh 정책 |
| `docs/DW_UPDATE_STRATEGY.md` | SQLite 최신값 upsert, row_hash, change event 전략 |
| `docs/YEARLY_CHANGE_ANALYSIS.md` | 기존 yearly CSV와 새 yearly CSV의 변경 비교 분석 |
| `docs/CURRENT_SYSTEM_ANALYSIS.md` | 기존 시스템 분석 결과 |
| `docs/PRD.md` | 프로젝트 목적, 범위, 성공 기준 |
| `docs/DATA_SPEC.md` | 데이터 소스, 주요 컬럼, PK 후보, 데이터 검증 TODO |
| `docs/ARCHITECTURE.md` | 현재/목표 아키텍처, DW 계층 구조 |
| `docs/IMPLEMENTATION_PLAN.md` | 단계별 구현 계획 |

### 현재 코드 관련 문서

- 월간 API 수집: `script/monthly_api_collection.py`
- 수집 모듈: `script/work24_collector/`
- 연간 CSV 병합: `script/yearly_csv_merge.py`
- 기존/신규 yearly 비교: `script/compare_yearly_changes.py`
- 상세 사용법: `docs/API_MONTHLY_COLLECTION.md`

### 현재 단계

SQLite Data Warehouse 구현 전 단계입니다.

현재까지는 기존 CSV 기반 운영을 안정화하기 위해 다음을 완료했습니다.

- 월간 API 수집 코드 개선
- `.env` 기반 API key 관리
- checkpoint/resume
- chunk append 저장
- 병렬 수집 옵션
- `all`, `non-national-card` API 그룹
- 월간 CSV와 연간 CSV 폴더 분리
- Power BI import용 yearly CSV merge
- 기존 yearly CSV와 신규 yearly CSV 차이 분석
- daily rolling refresh 정책 정리
- SQLite row_hash 기반 최신값 upsert 및 변경 이벤트 전략 정리

다음 주요 작업은 실제 CSV 데이터 분석 후 SQLite DW 설계입니다.
