# Next Context Handoff

Last updated: 2026-07-11

## Project Direction

SmartHRD is migrating from a CSV-centered Power BI workflow to a SQLite Data Warehouse workflow.

Current target architecture:

```text
Work24 API
-> Python ETL
-> SQLite Data Warehouse
-> Power BI
-> Fabric
```

Power BI must remain an analysis and visualization layer. SQLite is the future Single Source of Truth.

## Current Phase

The project is still before SQLite DW implementation.

Recent work focused on stabilizing the existing API collection path and preparing CSV exports that keep the current Power BI workflow usable.

This work is transitional. It should not be treated as the final DW architecture.

## Completed In This Context

### Existing-System Analysis

Created:

```text
docs/CURRENT_SYSTEM_ANALYSIS.md
```

Purpose:

- Record the current Python collection script behavior.
- Record current CSV/Power BI migration observations.
- Avoid repeating the same analysis in later contexts.

### Monthly API Collection Refactor

Created/updated:

```text
script/monthly_api_collection.py
script/work24_collector/config.py
script/work24_collector/client.py
script/work24_collector/collector.py
script/work24_collector/dates.py
script/work24_collector/env.py
script/work24_collector/storage.py
script/work24_collector/__init__.py
docs/API_MONTHLY_COLLECTION.md
.env.example
```

Main behavior:

- Collects Work24 API data by month.
- Supports `.env` based API keys.
- Splits arbitrary date ranges into monthly periods.
- Writes CSV output under `dataset/work24/monthly` by default.
- Writes checkpoints under `logs/checkpoints`.
- Writes run logs under `logs/api_collection_runs.csv`.
- Supports resume from checkpoint and existing CSV row count.
- Uses chunk append instead of rewriting the whole CSV.
- Logs intermediate save path, row count, timestamp, and speed.
- Preserves raw API response columns.

### Supported APIs

CLI API choices:

```text
national-card
employer
consortium
work-study
all
non-national-card
```

Collection order:

```text
all:
national-card -> employer -> consortium -> work-study

non-national-card:
employer -> consortium -> work-study
```

### Parallel Collection

Implemented conservative page-level parallel fetching.

Key options:

```text
--workers 1-4
--page-size 1-100
--save-every-pages
--progress-every-pages
--resume
--simple-filename
```

Observed speeds:

- Sequential collection was around 3 pages/s in user testing.
- `--workers 2` reached about 7 pages/s.
- `--workers 3` reached about 12-15 pages/s depending on server/network condition.
- `--workers 4` reached about 16.7 pages/s, but the gain over 3 workers was small.

Operational decision:

```text
Regular collection: workers=2
Manual large backfill: workers=3
Workers=4: test or one-off only
```

Avoid running overlapping jobs for the same API and same month because they would write the same CSV and checkpoint.

### Two-Terminal Backfill Pattern

Recommended pattern:

```powershell
# Terminal 1
python script\monthly_api_collection.py --api national-card --start 20240101 --end 20241231 --simple-filename --resume --workers 3 --progress-every-pages 10

# Terminal 2
python script\monthly_api_collection.py --api non-national-card --start 20240101 --end 20241231 --simple-filename --resume --workers 2 --progress-every-pages 10
```

This keeps the large national-card API separate from the three smaller APIs.

### Refresh Policy

Created:

```text
docs/REFRESH_POLICY.md
```

Current policy:

| Frequency | Refresh Window |
| --- | --- |
| Daily rolling refresh | Current month -12 months through current month +6 months |
| Manual | Full available period only when needed |

Weekly and monthly scheduled refreshes were removed because they overlap with daily rolling refresh.

Rationale:

- WAU is about 50.
- Local PC is not high-end.
- API does not provide a reliable modified timestamp or change log.
- Courses are often about 6 months, but long courses can run much longer.
- Future 6 months should be collected because upcoming recruiting/opening courses matter for Power BI.

### SQLite Update Strategy

Created:

```text
docs/DW_UPDATE_STRATEGY.md
```

Current decision:

```text
latest-value current tables
row_hash based upsert
lightweight row_change_event
no full old/new value history in the first version
```

Recommended first SQLite tables:

```text
raw_current_<api>
etl_run_log
row_change_event
```

Change-event intent:

- Keep current rows simple and latest-value oriented.
- Record when a row changed.
- Record which columns changed.
- Avoid storing full previous and new row values.
- Preserve enough evidence to tune refresh windows later.

### Yearly CSV Merge

Created:

```text
script/yearly_csv_merge.py
```

Purpose:

- Keep monthly CSV as the raw collected export.
- Create yearly CSV snapshots for easier Power BI import.

Input:

```text
dataset/work24/monthly/<API folder>/<API display name>_YYYYMM.csv
```

Output:

```text
dataset/work24/yearly/<API folder>/<API display name>_YYYY.csv
```

Important filtering:

- Only files matching `API name_YYYYMM.csv` are merged.
- Older files such as `YYYY년도_총...csv` are ignored.

Example commands:

```powershell
python script\yearly_csv_merge.py --api national-card --year 2024 --overwrite
python script\yearly_csv_merge.py --api non-national-card --year 2024 --overwrite
python script\yearly_csv_merge.py --api all --overwrite
```

The merge streams rows line by line and does not load the whole yearly dataset into memory.

Validation performed:

```text
python -m py_compile script\yearly_csv_merge.py
python script\yearly_csv_merge.py --help
python script\yearly_csv_merge.py --api consortium --year 2023 --yearly-dir tmp\yearly-test --overwrite
```

Observed test result:

```text
국가인적자원개발 컨소시엄 2023
months=12
rows=15778
```

The temporary test output was deleted.

## Important Operating Concepts

### Monthly Files

Monthly files are closer to raw collected exports and should be preserved.

```text
dataset/work24/monthly
```

### Yearly Files

Yearly files are Power BI-friendly snapshots.

```text
dataset/work24/yearly
```

They are reproducible from monthly files and should be regenerated after monthly data is refreshed.

### Snapshot Meaning

A snapshot is a file representing the data state at the time it was generated.

If historical API data changes later, the monthly file must be recollected and the yearly file must be regenerated.

## Current Recommended Commands

Show monthly collection help:

```powershell
python script\monthly_api_collection.py --help
```

Daily rolling refresh example for 2026-07-11:

```powershell
python script\monthly_api_collection.py --api all --start 20250701 --end 20270131 --simple-filename --resume --workers 2 --progress-every-pages 10
```

Collect national-card:

```powershell
python script\monthly_api_collection.py --api national-card --start 20240101 --end 20241231 --simple-filename --resume --workers 3 --progress-every-pages 10
```

Collect the other three APIs:

```powershell
python script\monthly_api_collection.py --api non-national-card --start 20240101 --end 20241231 --simple-filename --resume --workers 2 --progress-every-pages 10
```

Merge yearly CSV after collection completes:

```powershell
python script\yearly_csv_merge.py --api all --overwrite
```

## Things Not Done Yet

SQLite DW has not been built.

Not implemented yet:

- SQLite schema
- Raw/staging/dimension/fact/mart tables
- SQLite load process
- Row hash change detection
- Lightweight row change event log
- Power BI SQLite connection
- Windows Scheduler automation
- Fabric refresh automation

## Next Recommended Work

### 1. Finish Current CSV Backfill

Before moving into SQLite, finish or verify the current monthly collection:

- Confirm all required months exist under `dataset/work24/monthly`.
- Confirm checkpoint files indicate successful completion.
- Confirm run logs do not contain failed periods.
- Regenerate `dataset/work24/yearly` after collection completes.

### 2. Analyze Current CSV Data

This is the best next architecture task.

Analyze actual monthly/yearly CSVs for:

- Columns
- Data types
- Null rates
- Duplicate rows
- PK candidates
- FK candidates
- Date columns
- API-specific schema differences

Do not infer these from API docs only. Confirm with real CSV files.

### 3. Design SQLite DW

After CSV analysis:

- Define raw table strategy.
- Define staging normalization rules.
- Confirm PK for course offerings.
- Use latest-value upsert per API as the first implementation direction.
- Define row hash fields for change detection.
- Define `row_change_event` structure.
- Design ETL run log table.

### 4. Build SQLite Incrementally

Start with raw load only.

Do not immediately replace Power BI.

Recommended sequence:

```text
raw load
-> validation reports
-> staging tables
-> dimension/fact candidates
-> Power BI comparison
```

## Cautions For Next Context

- Do not remove CSV yet.
- Do not modify Power BI yet.
- Do not delete old API response columns.
- Do not put API keys in code.
- Avoid overlapping parallel runs for the same API/month.
- Do not treat yearly CSV as the Single Source of Truth.
- SQLite DW is still the target Single Source of Truth.
