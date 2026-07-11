# Refresh Policy

## Purpose

This document defines the practical refresh policy for SmartHRD collection while the project is still running on a local Windows PC and CSV/SQLite migration is in progress.

The policy intentionally avoids excessive traffic and local computation.

## Current Assumptions

- Weekly active users are about 50.
- Collection runs on a local Windows 10 PC.
- The API does not provide a reliable modified timestamp or change log.
- Training courses commonly run for about 6 months.
- Some long courses can have large training hours, such as 1500 hours.
- Course data may change while the course is recruiting or operating.

## Refresh Schedule

Only one scheduled refresh is kept.

| Frequency | Refresh Window | Purpose |
| --- | --- | --- |
| Daily | Current month -12 months through current month +6 months | Cover long-running courses, recent updates, current recruiting, and near-future courses. |
| Manual | Full available period | Use only when API behavior changes, Power BI results look wrong, or historical validation is needed. |

Weekly and monthly scheduled refreshes are intentionally removed.

Reason:

- They overlap with daily refresh windows.
- They create duplicate scheduled work.
- A single daily rolling window is easier to operate and reason about.
- Future SQLite row-hash upsert will make unchanged rows cheap to process.

Example for 2026-07-11:

```text
Daily rolling refresh:
2025-07-01 through 2027-01-31
```

The window is month-based, not exact-day based.

## Operating Principle

The refresh strategy prioritizes:

1. Low traffic and low local compute.
2. Accuracy for current, recently operating, and near-future courses.
3. Coverage for long-running courses and late corrections.
4. Manual full refresh only when there is a clear reason.

## Future SQLite DW Note

When SQLite loading is implemented, each refresh should support change detection by storing row hashes.

Suggested comparison fields:

- `source_api`
- `trprId`
- `trprDegr`
- `trainstCstId`
- `traStartDate`
- `traEndDate`
- `row_hash`
- `collected_at`

If the API still has no modified timestamp, this project should detect changes by comparing current row hashes with previously stored rows.

The first SQLite design should keep latest values in current tables and store lightweight change events.

Recommended extra tables:

```text
etl_run_log
row_change_event
```

`row_change_event` should store when a row changed and which columns changed, without storing full old/new values.

See:

```text
docs/DW_UPDATE_STRATEGY.md
```
