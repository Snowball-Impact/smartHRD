# CSV Warehouse 정기 ETL Demo 파이프라인 준비

## 오늘 작업 사항

- 프로젝트 방향을 SQLite DW에서 CSV Warehouse 기반 Demo 데이터 플랫폼으로 정리했습니다.
- README, AGENTS, PRD, DATA_SPEC, ARCHITECTURE, IMPLEMENTATION_PLAN을 CSV Warehouse 운영 기준으로 갱신했습니다.
- Demo ETL 진입점 `script/csv_warehouse_etl.py`를 추가했습니다.
  - 오늘 날짜 기준 refresh window 계산
  - `--months-back`, `--months-forward` 인자 지원
  - 고용24 API 월별 수집
  - Validation 통과 시 yearly CSV 재생성
  - Validation 실패 시 기존 yearly CSV 유지
  - `warehouse/logs/etl_log.csv` 기록
  - `warehouse/logs/data_snapshot_log.csv` checksum 변경 로그 기록
- Windows Task Scheduler용 `script/run_csv_warehouse_etl.bat`를 추가했습니다.
  - 기본값은 과거 6개월 / 미래 6개월
  - 실행 인자 또는 `SMART_HRD_MONTHS_BACK`, `SMART_HRD_MONTHS_FORWARD` 환경변수로 범위 변경 가능
- CSV Warehouse 운영 문서 `docs/CSV_WAREHOUSE_PLATFORM.md`를 추가했습니다.
- 기존 collector가 ETL에서 expected_count를 집계할 수 있도록 수집 결과를 반환하게 수정했습니다.
- `python -m py_compile` 및 배치 파일 `--help` 전달 동작을 확인했습니다.

## 현재 보류한 사항

- 실제 API key / 네트워크 환경에서 end-to-end 정기 ETL 리허설은 다음 주에 수행합니다.
- Power BI 원본 경로는 현재 변경하지 않습니다.
- 운영 ETL 로그 파일은 실제 ETL 실행 시 `warehouse/logs/etl_log.csv`와 `warehouse/logs/data_snapshot_log.csv`로 생성됩니다.

## 다음 작업

- [ ] 다음 주 정기 업데이트 전 `.env` API key 확인
- [ ] `script/run_csv_warehouse_etl.bat` 또는 `script/csv_warehouse_etl.py`로 수동 리허설 실행
- [ ] `warehouse/logs/etl_log.csv` 생성 및 PASS/FAIL 확인
- [ ] FAIL 발생 시 `message`와 월별 `api_collection_runs.csv` 확인
- [ ] PASS 발생 시 `dataset/work24/yearly` 생성/교체 확인
- [ ] Validation 기준이 실제 API 데이터에 너무 엄격한지 확인
- [ ] 필요 시 필수 컬럼 NULL 허용 정책 조정

## 참고

Demo 운영 기준에서는 Power BI가 `dataset/work24/yearly` 원본을 계속 사용합니다.
