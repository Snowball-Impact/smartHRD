# GitHub Issue Draft

## Title

Work24 CSV collection stabilization and SQLite DW update strategy

## Body

## Summary

This issue records the completed stabilization work for the Work24 API collection pipeline and the design decisions for the upcoming SQLite Data Warehouse migration.

## Completed

- Refactored monthly Work24 API collection into reusable Python modules.
- Added `.env` based API key loading.
- Added checkpoint/resume support.
- Added chunk append CSV writes.
- Added intermediate save logs with file path, row count, timestamp, and speed.
- Added conservative parallel page fetching with `--workers`.
- Added `all` and `non-national-card` API groups.
- Moved Work24 CSV outputs under `dataset/work24/monthly` and `dataset/work24/yearly`.
- Added yearly CSV merge script for Power BI-friendly yearly snapshots.
- Added checkpoint-based validation to prevent incomplete monthly CSV files from being merged.
- Added existing-vs-new yearly CSV comparison script.
- Documented observed yearly changes and the need for row-hash based change detection.
- Documented daily rolling refresh policy.

## Current Refresh Policy

Scheduled refresh:

```text
Daily rolling refresh:
current month -12 months through current month +6 months
```

Manual refresh:

```text
Full available period only when API behavior changes, data quality investigation is needed, or historical validation is required.
```

## SQLite DW Direction

First SQLite implementation should prioritize raw/current stability before dimensional modeling.

Initial table direction:

```text
raw_current_<api>
etl_run_log
row_change_event
```

Update strategy:

- Keep latest row values in current tables.
- Use row identity key plus `row_hash` for upsert/change detection.
- Store lightweight `row_change_event` records.
- Do not store full old/new row values in the first version.

## Row Identity Candidate

```text
source_api
trprId
trprDegr
trainstCstId
traStartDate
traEndDate
```

This candidate must still be validated across all target monthly/yearly CSVs before final SQLite constraints are created.

## Key Documents

- `README.md`
- `docs/NEXT_CONTEXT_HANDOFF.md`
- `docs/API_MONTHLY_COLLECTION.md`
- `docs/REFRESH_POLICY.md`
- `docs/DW_UPDATE_STRATEGY.md`
- `docs/YEARLY_CHANGE_ANALYSIS.md`
- `docs/DATA_SPEC.md`
- `docs/ARCHITECTURE.md`
- `docs/IMPLEMENTATION_PLAN.md`

## Next Work

- Add refresh-window date calculation to the collection CLI.
- Profile actual CSV files for columns, types, nulls, duplicates, PK/FK candidates, and date columns.
- Design SQLite `raw_current_<api>`, `etl_run_log`, and `row_change_event`.
- Implement row-hash based SQLite upsert.
- Validate SQLite outputs against current CSV/yearly snapshots.

