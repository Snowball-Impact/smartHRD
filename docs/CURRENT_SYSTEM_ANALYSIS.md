# Current System Analysis

## Purpose

This document records the current SmartHRD system analysis before SQLite Data Warehouse implementation.

The project is still in the analysis and design phase. No ETL refactoring, SQLite build, Power BI model change, or API behavior change has been performed.

## Documents Reviewed

Reviewed in order:

1. `README.md`
2. `AGENTS.md`
3. `docs/PRD.md`
4. `docs/DATA_SPEC.md`
5. `docs/ARCHITECTURE.md`
6. `docs/IMPLEMENTATION_PLAN.md`
7. `BACKLOG.md`

Key constraints from the documents:

- Preserve existing Power BI results.
- Do not delete or modify API source columns in the raw layer.
- Keep CSV during migration; do not remove it immediately.
- SQLite becomes the single source of truth.
- Power BI is used only for analysis and visualization.
- ETL order should be Extract -> Validate -> Transform -> Load.
- API keys must not be stored in code; use `.env`.
- Every ETL run should be logged.

## Project Structure

Current important paths:

- `web/scraping.py`: web scraping script for KSQA notice data.
- `script/통합_목록_스크래핑.ipynb`: main notebook containing 고용24 API collection logic.
- `dataset/`: CSV, XLSX, and spatial data files.
- `Dashboard/`: Power BI PBIX files.
- `docs/`: project planning and specification documents.

Latest Power BI file by timestamp:

- `Dashboard/국민내일배움카드훈련과정_대시보드_v1.6.3.pbix`

## Current Data Flow

Current target migration:

```text
고용24 API
  -> Python ETL
  -> SQLite Data Warehouse
  -> Power BI
  -> Fabric
```

Current actual structure:

```text
고용24 API
  -> CSV
  -> Power BI
```

Additional current source:

```text
KSQA website
  -> web/scraping.py
  -> 심사평가원_심사평가공고.csv
```

## Python Collection Scripts

### `web/scraping.py`

This script does not collect 고용24 API data. It scrapes the KSQA website.

Observed flow:

1. Starts headless Selenium Chrome.
2. Opens `https://www.ksqa.or.kr/?pid=HP010201`.
3. Parses page HTML with BeautifulSoup.
4. Extracts notice title, URL, and registration date from `table.table_list`.
5. Saves CSV with UTF-8-SIG encoding.

Output filename is derived from `pid`:

- `HP010201` -> `심사평가원_심사평가공고.csv`

### `script/통합_목록_스크래핑.ipynb`

This notebook contains the main 고용24 API collection logic.

Main API list endpoints observed:

- 국민내일배움카드: `310L01`
- 사업주훈련: `311L01`
- 국가인적자원개발 컨소시엄: `312L01`
- 일학습병행: `313L01`
- 채용정보: `210L01`

Important notebook functions:

- `URLcombine(start, end, pageNum=1)`: builds API URL.
- `URLcall(url, pageNum=1)`: calls URL and converts response to JSON.
- `URLdataCheck(resp_json, url)`: checks `srchList` length and retries empty responses up to 3 times.
- `month_period(start, end)`: creates month start and month end ranges.
- `dataMerge(total_df, resp_json)`: appends `srchList` to accumulated DataFrame.
- `toCSV(total_df, fname, start, end, scn_cnt)`: saves CSV and marks missing count in filename if incomplete.
- `APIcollection(start, end, page_size=100, pageNum=1)`: controls paged collection for a date range.

Current collection pattern:

1. User defines API type and date range.
2. First API call retrieves `scn_cnt`.
3. `goal_cnt = ceil(scn_cnt / page_size)`.
4. Iterate pages.
5. Append each page's `srchList`.
6. Save every 100 pages.
7. Save final CSV when page count reaches goal.

## Script Issues

Observed issues:

- API keys are hardcoded in the notebook. The exact key values are intentionally not repeated here.
- Error handling is print-based and does not guarantee recovery.
- `except Exception` logs the error, waits 1 second, then `pass`es.
- Restart/recovery is manual through `pageNum` and `lastSavePath`.
- No structured ETL log exists yet.
- No persistent run metadata exists yet.
- API extraction, validation, transformation, and loading are mixed in notebook cells.
- Raw API preservation is not separated from analysis cleanup.
- Some later notebook cells drop columns or remove `regCourseMan == 0` rows. That may be useful for mart logic, but should not happen in raw.
- Detailed API endpoint `310L03` is explored, but the code is less organized than list collection and includes execution-error traces.

## CSV Structure

### 국민내일배움카드 목록

Observed 30 columns:

```text
eiEmplCnt3Gt10, eiEmplRate6, eiEmplCnt3, eiEmplRate3,
certificate, title, realMan, telNo, stdgScor, traStartDate,
grade, ncsCd, regCourseMan, trprDegr, address, traEndDate,
subTitle, instCd, trngAreaCd, trprId, yardMan, courseMan,
wkendSe, trainTarget, trainTargetCd, trainstCstId, contents,
subTitleLink, titleLink, titleIcon
```

Core candidate business columns:

- `trprId`: training course ID
- `trprDegr`: training course round
- `trainstCstId`: training institution customer ID
- `instCd`: institution code
- `ncsCd`: NCS code
- `traStartDate`: training start date
- `traEndDate`: training end date
- `trainTargetCd`: training target code
- `regCourseMan`: registered participants
- `yardMan`: capacity
- `courseMan` / `realMan`: cost-related numeric fields observed in reports
- `stdgScor`: satisfaction score

### Other Training List CSVs

사업주훈련, 국가인적자원개발 컨소시엄, 일학습병행 use a common 24-column shape:

```text
certificate, title, realMan, telNo, traStartDate, grade,
ncsCd, regCourseMan, trprDegr, address, traEndDate, subTitle,
instCd, trngAreaCd, trprId, yardMan, courseMan, trainTarget,
trainTargetCd, trainstCstId, contents, subTitleLink, titleLink,
titleIcon
```

### Supporting CSVs

Observed supporting data:

- `2025년기준_목록추출_기관ID과정ID기수.csv`
  - `trainstCstId`, `trprId`, `trprDegr`
- `고용24API_국민내일배움카드훈련과정_과정기관기초정보_총3835개 중의 3835개_훈련기관ID기준.csv`
  - 29 columns including detailed provider/course fields.
- `훈련기관주소.csv`
  - `subTitle`, `trngAreaCd`, `addr1`
- `직업능력심사평가원/심사평가원_심사평가공고.csv`
  - `제목`, `URL`, `등록일`

## CSV Data Findings

### 국민내일배움카드

Actual row and key checks:

| File | Rows | Date Range | `trprId` Duplicate Rows | `trprId + trprDegr` Duplicate Rows |
| --- | ---: | --- | ---: | ---: |
| `국민내일배움카드훈련과정_2023~2025년.csv` | 749,067 | 2023-02-01 ~ 2025-12-31 | 707,856 | 100 |
| `국민내일배움카드훈련과정_2026년.csv` | 232,206 | 2026-01-01 ~ 2026-03-31 | 213,516 | 0 |
| `국민내일배움카드훈련과정_202604.csv` | 85,352 | 2026-04-01 ~ 2026-04-30 | 73,559 | 0 |
| `국민내일배움카드훈련과정_202605.csv` | 81,471 | 2026-05-01 ~ 2026-05-31 | 70,223 | 100 |
| `국민내일배움카드훈련과정_202606.csv` | 84,248 | 2026-06-01 ~ 2026-06-30 | 72,450 | 0 |

Observed:

- `trprId` alone is not a primary key.
- `trprId + trprDegr` is a strong candidate, but not always unique.
- `trprId + trprDegr + trainstCstId` also had the same 100 duplicate rows in affected files.
- Raw tables should not rely only on the business key. Add load metadata or surrogate key.

High-null columns in 국민내일배움카드:

- `eiEmplCnt3Gt10`
- `grade`
- `contents`
- `eiEmplRate6`
- `eiEmplCnt3`
- `eiEmplRate3`
- `certificate`

Other nullable columns observed:

- `telNo`
- `ncsCd`
- `titleIcon`

### 사업주훈련, 컨소시엄, 일학습병행

For files checked, `trprId + trprDegr` was unique within each file.

Important observations:

- 사업주훈련 has some null `trainTarget` and `trainTargetCd`.
- 일학습병행 has files where `instCd` is entirely null.
- `trprId` alone is highly duplicated across all training-list datasets.

## Power BI Model Findings

Latest PBIX inspected:

- `Dashboard/국민내일배움카드훈련과정_대시보드_v1.6.3.pbix`

PBIX internal metadata shows:

- Created from Cloud.
- Power BI release: `2026.04`.
- Remote dataset/report IDs exist in `Connections`.

Model nodes found in `DiagramLayout`:

- `NCS통합분류코드`
- `DimDate`
- `목록_통합`
- `공지사항_고용24`
- `공지사항_고용노동부`
- `공지사항_능력개발교육원`
- `공지사항_심사평가원`
- `심사평가공고_심사평가원`
- `보도자료_고용노동부`
- `훈련지역시군구분류코드`
- `훈련지역대분류코드`
- `네이버뉴스API_내일배움카드`
- `네이버뉴스API_부트캠프`
- `네이버뉴스API_직업훈련`
- parameter tables
- `WebView`

Report layout heavily references:

- `목록_통합`
- `국민내일배움카드훈련과정_목록`
- `DimDate`
- `NCS통합분류코드`
- `훈련지역분류코드`
- `훈련지역시군구분류코드`
- notice/news tables

Observed measures or calculated outputs in visuals:

- `모집율`
- `총매출액`
- `포화율`
- `RowNumber순번`

Important limitation:

- Full Power BI relationship and Power Query extraction was not completed because `DataModel` is binary and `pbi-tools` is not installed in the environment.

## Fact and Dimension Candidates

### Fact Candidates

Primary fact candidate:

- `fact_training_course_run`

Likely grain candidate:

```text
source_api + trprId + trprDegr + trainstCstId + traStartDate + traEndDate
```

This grain must not be finalized yet because duplicate rows were observed in 국민내일배움카드 files.

Power BI mart candidate:

- `mart_training_course_list`

This should reproduce the current `목록_통합` behavior for Power BI compatibility.

### Dimension Candidates

Candidate dimensions:

- `dim_date`
- `dim_training_provider`
- `dim_course`
- `dim_ncs`
- `dim_region`
- `dim_training_target`
- `dim_source_api`

Candidate provider keys:

- `trainstCstId`
- `instCd`
- `subTitle`

Candidate course keys:

- `trprId`
- `title`
- `ncsCd`
- `trainTargetCd`

## SQLite DW Transition Direction

Recommended layer design:

```text
raw
  -> staging
  -> dimension
  -> fact
  -> mart
```

### Raw

Store source responses as-is.

Recommended raw metadata columns:

- `raw_id`
- `source_api`
- `source_endpoint`
- `source_file`
- `source_period_start`
- `source_period_end`
- `page_num`
- `load_batch_id`
- `loaded_at`

Do not drop API columns in raw.

### Staging

Perform validation and type normalization:

- Parse date fields.
- Normalize numeric fields.
- Preserve code fields as text if leading zeros are possible.
- Detect duplicate business keys.
- Add validation status and error message fields if needed.

### Dimension and Fact

Build dimensions only after business key validation.

Do not make `trprId` the primary key.

Do not finalize `trprId + trprDegr` as primary key until duplicate rows are investigated.

### Mart

Build mart tables/views that reproduce existing Power BI tables, especially:

- `목록_통합`
- `국민내일배움카드훈련과정_목록`

Power BI migration should first connect to mart outputs, then compare totals with existing CSV-based model.

## Improvement Points

Recommended improvements for the implementation phase:

- Move API keys to `.env`.
- Convert notebook logic into Python modules.
- Separate Extract, Validate, Transform, Load.
- Add structured retry with max attempts, backoff, and failure logging.
- Add checkpoint table/file for resumable collection.
- Add ETL run log table.
- Preserve raw API response columns.
- Keep CSV export as compatibility output during migration.
- Add duplicate validation reports.
- Add row count and measure comparison between CSV and SQLite mart.
- Extract Power BI relationships using a dedicated tool before changing the model.

## Open TODO

- Investigate the exact 100 duplicated 국민내일배움카드 rows.
- Extract full Power Query M scripts from PBIX.
- Extract full Power BI relationship metadata.
- Build a data dictionary for all CSV columns.
- Confirm whether `courseMan` and `realMan` are used as cost fields in the current dashboard.
- Confirm exact logic for `목록_통합`.
- Confirm exact logic for measures: `모집율`, `총매출액`, `포화율`.
- Decide raw table strategy for monthly files vs API direct loads.
- Decide whether current CSV filenames represent collection period or training start date period.
- Define SQLite naming convention.
- Define ETL log schema.

