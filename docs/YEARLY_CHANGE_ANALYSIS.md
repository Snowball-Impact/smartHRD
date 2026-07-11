# Yearly Change Analysis

Last updated: 2026-07-11

## Purpose

This document records the first comparison between old yearly CSV snapshots in the deleted backup area and newly collected/merged yearly CSV snapshots in `dataset/work24/yearly`.

The goal is to understand whether newly collected API data differs from the existing Power BI-era CSV data before designing SQLite update logic.

## Scope

Compared years:

```text
2023
2024
```

Compared APIs:

```text
national-card
employer
consortium
work-study
```

Comparison key:

```text
trprId + trprDegr + trainstCstId + traStartDate + traEndDate
```

This key was checked against 2024 yearly files and had no duplicate keys in both old and new snapshots.

## Script

Created:

```text
script/compare_yearly_changes.py
```

Usage:

```powershell
python script\compare_yearly_changes.py --api all
python script\compare_yearly_changes.py --api non-national-card --write-details
```

The script compares row identity by the key above and row changes by hashing comparable columns.

## Output

Generated:

```text
analysis/changes/summary.csv
analysis/changes/column_change_summary.csv
```

Detailed changed-row outputs were generated for:

```text
analysis/changes/employer_2023/
analysis/changes/employer_2024/
analysis/changes/consortium_2023/
analysis/changes/consortium_2024/
analysis/changes/work-study_2023/
analysis/changes/work-study_2024/
```

Each detail folder contains:

```text
added_rows.csv
removed_rows.csv
changed_rows_new.csv
changed_cells.csv
```

National-card detail files were intentionally not generated yet because the output would be large and 2024 includes incomplete monthly collection files.

## Summary

| API | Year | Old Rows | New Rows | Added | Removed | Changed Rows | Notes |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| national-card | 2023 | 586,289 | 586,287 | 0 | 2 | 586,265 | Large column-format/value changes, especially `ncsCd` and `stdgScor`. |
| national-card | 2024 | 607,773 | 607,772 | 0 | 1 | 607,746 | Rechecked after recollecting incomplete monthly files. |
| employer | 2023 | 396,546 | 396,546 | 0 | 0 | 286,406 | Mostly `ncsCd` changes. |
| employer | 2024 | 337,566 | 337,565 | 0 | 1 | 249,227 | Mostly `ncsCd` changes. |
| consortium | 2023 | 15,778 | 15,778 | 0 | 0 | 4,032 | Mostly `ncsCd`, `address`, `trngAreaCd`. |
| consortium | 2024 | 17,506 | 17,506 | 0 | 0 | 4,676 | Mostly `ncsCd`, `address`, `trngAreaCd`. |
| work-study | 2023 | 6,478 | 6,478 | 0 | 0 | 6,477 | Mostly `trngAreaCd`, then `ncsCd`. |
| work-study | 2024 | 6,692 | 6,692 | 0 | 0 | 6,688 | Mostly `trngAreaCd`, then `ncsCd`. |

## Column-Level Findings

Most frequent changed columns:

| API | Year | Main Changed Columns |
| --- | ---: | --- |
| national-card | 2023 | `ncsCd` 585,941; `stdgScor` 419,424; `eiEmplCnt3` 28,310 |
| national-card | 2024 | `ncsCd` 607,457; `stdgScor` 427,388; `eiEmplCnt3` 32,943 |
| employer | 2023 | `ncsCd` 285,933 |
| employer | 2024 | `ncsCd` 248,782 |
| consortium | 2023 | `ncsCd` 2,778; `address` 1,188; `trngAreaCd` 631 |
| consortium | 2024 | `ncsCd` 2,776; `address` 1,757; `trngAreaCd` 450 |
| work-study | 2023 | `trngAreaCd` 6,477; `ncsCd` 1,425 |
| work-study | 2024 | `trngAreaCd` 6,687; `ncsCd` 1,641 |

## Important Data Quality Finding

The initially generated national-card 2024 yearly file was incomplete and should not be used for final difference interpretation.

Suspicious monthly files:

```text
dataset/work24/monthly/국민내일배움카드/국민내일배움카드훈련과정_202405.csv
dataset/work24/monthly/국민내일배움카드/국민내일배움카드훈련과정_202409.csv
```

Observed row counts:

```text
202405: 100 rows
202409: 10,000 rows
```

Related checkpoint status:

```text
202405 expected_count=49,813 collected_count=100
202409 expected_count=48,470 collected_count=10,000
```

Therefore, the 88,184 removed rows in national-card 2024 are likely caused mainly by incomplete collection, not real API deletions.

After recollecting those two months and regenerating the 2024 yearly file, the updated comparison is:

```text
old_rows=607,773
new_rows=607,772
shared_rows=607,772
added_rows=0
removed_rows=1
changed_rows=607,746
unchanged_rows=26
```

Follow-up protection added:

```text
script/yearly_csv_merge.py
```

The yearly merge now validates monthly CSV row counts against checkpoint `expected_count` before merging.
Incomplete monthly files stop the merge unless `--allow-incomplete` is explicitly passed.

## Interpretation

The old and new snapshots often have the same row identities but different field values.

This strongly supports the need for row-hash based change detection in SQLite.

The largest observed differences are not additions/removals but updates to existing course rows.

Current SQLite update decision:

```text
Keep latest values in current tables.
Use row_hash for upsert/change detection.
Store lightweight row_change_event records.
Do not store full old/new values in the first version.
```

Likely high-impact columns for update tracking:

```text
ncsCd
stdgScor
trngAreaCd
address
telNo
subTitle
employment outcome fields in national-card
```

## Next Actions

1. Recollect incomplete national-card months before using 2024 national-card diff.
2. Inspect sample rows from `changed_cells.csv` to classify whether changes are value corrections, code-format changes, or API behavior changes.
3. Add row-hash strategy to SQLite raw/current design.
4. Store latest values plus lightweight `row_change_event`.
5. Use change events to tune the daily rolling refresh window later.

## Cautions

- Do not treat all `changed_rows` as business-significant changes.
- Some changes may be API code normalization or field-format changes.
- National-card 2024 must be recollected before final validation.
- Yearly CSV is a snapshot, not the Single Source of Truth.
- Full old/new value history is intentionally deferred.
