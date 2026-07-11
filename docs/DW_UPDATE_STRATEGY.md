# DW Update Strategy

Last updated: 2026-07-11

## Purpose

This document records the current design decision for future SQLite Data Warehouse updates.

The goal is to keep the operational model simple while still collecting enough change evidence to tune refresh windows later.

## Current Decision

Use a daily rolling refresh and SQLite upsert.

```text
Daily rolling refresh
-> collect Work24 API rows
-> compute row identity key
-> compute row_hash
-> upsert current row
-> record lightweight change event
```

## Refresh Window

Only one scheduled refresh type is kept.

| Type | Window | Purpose |
| --- | --- | --- |
| Daily rolling refresh | Current month -12 months through current month +6 months | Cover long-running courses, recent updates, current recruiting, and near-future courses. |
| Manual full refresh | Full available period | Use only for API behavior changes, data quality investigation, or historical revalidation. |

Weekly and monthly scheduled refreshes are intentionally removed to avoid overlapping schedules and duplicate work.

Example for 2026-07-11:

```text
Daily rolling refresh target:
2025-07-01 through 2027-01-31
```

The window should be calculated by month, not by exact day count.

## Row Identity

Initial row identity candidate:

```text
source_api
trprId
trprDegr
trainstCstId
traStartDate
traEndDate
```

This key was validated against yearly comparison work and had no duplicates in checked 2024 yearly files.

The key must still be validated across all target monthly/yearly CSV files before final SQLite constraints are created.

## Latest-Value Current Table

The main serving/raw-current table keeps the latest row value only.

Recommended metadata columns:

```text
source_api
row_hash
created_at
updated_at
last_seen_at
is_active
missing_since
```

Meaning:

| Column | Meaning |
| --- | --- |
| `created_at` | First time this row identity was seen. |
| `updated_at` | Last time the row content changed. |
| `last_seen_at` | Last time the row identity appeared in the API result. |
| `is_active` | Whether the row is currently considered active/visible. |
| `missing_since` | First time the row stopped appearing within an expected refresh window. |
| `row_hash` | Hash of comparable source columns for change detection. |

## Row Hash

`row_hash` is a stable hash generated from comparable source columns.

Processing rule:

```text
new key not found
-> INSERT current row

key found and row_hash differs
-> UPDATE current row and updated_at
-> INSERT row_change_event

key found and row_hash matches
-> UPDATE last_seen_at only
```

Raw API response columns must not be dropped from the raw/current layer.

## Change Event Log

Do not store full old/new row values in the first SQLite version.

Instead, store lightweight row-level change events.

Recommended table:

```text
row_change_event
```

Recommended columns:

```text
event_id
run_id
source_api
row_key
trprId
trprDegr
trainstCstId
traStartDate
traEndDate
old_row_hash
new_row_hash
changed_columns
changed_at
```

`changed_columns` can be stored as JSON text:

```json
["ncsCd", "stdgScor", "address"]
```

This stores when a row changed and which columns changed, without storing old and new values.

## Why Not Full Change History Yet

Full old/new value history is intentionally deferred.

Reasons:

- Current product need is latest-state Power BI analysis.
- Some API fields, such as `ncsCd`, changed for very large portions of historical rows.
- Full value history would increase SQLite size and ETL complexity.
- Lightweight change events are enough to tune refresh windows later.

## What This Allows Later

The change event table supports future policy tuning, for example:

```text
Which course months still change frequently?
How often do future courses change before start?
How long after traEndDate do rows continue changing?
Which columns drive most updates?
Can the -12 month window be reduced safely?
```

Example analysis:

```sql
SELECT
  substr(traStartDate, 1, 6) AS course_start_month,
  COUNT(*) AS changed_rows
FROM row_change_event
WHERE changed_at >= date('now', '-30 days')
GROUP BY substr(traStartDate, 1, 6)
ORDER BY course_start_month;
```

## Initial SQLite Scope

Recommended first SQLite implementation:

```text
raw_current_<api>
etl_run_log
row_change_event
```

Do not start with full dimension/fact modeling.

Recommended sequence:

```text
1. Load current rows into SQLite.
2. Add row_hash and metadata columns.
3. Implement upsert.
4. Record run summary and row_change_event.
5. Validate against CSV/yearly snapshots.
6. Design staging/dimension/fact after raw-current behavior is stable.
```

## Open Questions

- Should raw current tables be one table per API or one unified table with JSON/raw columns?
- Should `changed_columns` be calculated for all columns or exclude operational metadata columns?
- How should missing rows be marked inactive when refresh windows overlap only part of a year?
- Should generated yearly CSV exports eventually come from SQLite instead of monthly CSV?
