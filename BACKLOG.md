# Backlog

## 분석

- [x] 현재 수집 스크립트 분석
- [ ] Power BI current CSV 연결 영향 검증
- [ ] 운영 현황 Dashboard 요구사항 확정

## CSV Warehouse

- [x] CSV Warehouse 구조 정의
- [x] current/backup/logs/tmp 정책 정의
- [x] Validation 실패 시 current 유지 정책 구현

## ETL

- [x] API 모듈 분리
- [x] Demo ETL 진입점 작성
- [x] 주간 refresh window 계산
- [x] Validator 작성
- [x] ETL CSV 로그 작성
- [ ] 실제 API key 환경에서 end-to-end 수집 검증

## Power BI

- [ ] Power BI Desktop 원본을 `warehouse/current`로 연결
- [ ] On-premises Data Gateway 경로 등록
- [ ] Power BI Service 예약 새로고침 설정
- [ ] 운영 현황 Dashboard 페이지 설계

## Automation

- [x] Windows Scheduler 실행 배치 파일 작성
- [ ] Windows Scheduler 작업 등록
- [ ] 토요일 새벽 스케줄 실행 검증

