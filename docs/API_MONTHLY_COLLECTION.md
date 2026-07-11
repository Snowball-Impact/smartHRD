# API Monthly Collection

This document describes the updated monthly Work24 API collection script.

## Script

```text
script/monthly_api_collection.py
```

The script keeps the current CSV-based workflow while making monthly collection repeatable from the command line.

It does not build SQLite tables yet.

## Code Structure

The command stays the same, but the implementation is split into small modules:

| File | Role |
| --- | --- |
| `script/monthly_api_collection.py` | CLI argument parsing and entry point |
| `script/work24_collector/config.py` | API specs, defaults, settings dataclass |
| `script/work24_collector/env.py` | `.env` loading |
| `script/work24_collector/dates.py` | `YYYYMMDD` parsing and monthly range splitting |
| `script/work24_collector/client.py` | URL building, HTTP session reuse, retry logic |
| `script/work24_collector/storage.py` | CSV, checkpoint, and run-log file handling |
| `script/work24_collector/collector.py` | Monthly collection orchestration |
| `script/yearly_csv_merge.py` | Monthly-to-yearly CSV merge for Power BI import |

## Supported APIs

| CLI value | Dataset | Endpoint | Env key |
| --- | --- | --- | --- |
| `all` | All datasets below, in collection order | Multiple | All keys below |
| `non-national-card` | All supported APIs except 국민내일배움카드, in collection order | Multiple | Employer, consortium, and work-study keys |
| `national-card` | 국민내일배움카드훈련과정 | `310L01` | `WORK24_API_KEY_NATIONAL_CARD` |
| `employer` | 사업주훈련 | `311L01` | `WORK24_API_KEY_EMPLOYER` |
| `consortium` | 국가인적자원개발 컨소시엄 | `312L01` | `WORK24_API_KEY_CONSORTIUM` |
| `work-study` | 일학습병행 | `313L01` | `WORK24_API_KEY_WORK_STUDY` |

When `--api all` is used, APIs run sequentially in this order:

```text
national-card -> employer -> consortium -> work-study
```

When `--api non-national-card` is used, APIs run sequentially in this order:

```text
employer -> consortium -> work-study
```

## Environment

Copy `.env.example` to `.env` and fill the required API key.

Real API keys must not be committed.

## Example

Show available options, default values, and accepted ranges:

```powershell
python script\monthly_api_collection.py --help
```

Collect 국민내일배움카드 data for June 2026:

```powershell
python script\monthly_api_collection.py --api national-card --start 20260601 --end 20260630 --simple-filename --resume
```

Collect all supported APIs for June 2026:

```powershell
python script\monthly_api_collection.py --api all --start 20260601 --end 20260630 --simple-filename --resume --workers 2 --progress-every-pages 10
```

Collect the three non-national-card APIs for June 2026:

```powershell
python script\monthly_api_collection.py --api non-national-card --start 20260601 --end 20260630 --simple-filename --resume --workers 2 --progress-every-pages 10
```

Daily rolling refresh policy is documented in `docs/REFRESH_POLICY.md`.

The current collection CLI does not yet provide `--refresh-window daily`.
Until that option is implemented, calculate the month-based window manually and pass `--start` and `--end`.

Example for 2026-07-11:

```powershell
python script\monthly_api_collection.py --api all --start 20250701 --end 20270131 --simple-filename --resume --workers 2 --progress-every-pages 10
```

Output:

```text
dataset/work24/monthly/국민내일배움카드/국민내일배움카드훈련과정_202606.csv
```

Run log:

```text
logs/api_collection_runs.csv
```

Checkpoint:

```text
logs/checkpoints/national-card_20260601_20260630.json
```

## Behavior

- Splits a date range into month-sized periods.
- Calls the API with `returnType=json`, `outType=1`, `sort=ASC`, `sortCol=2`.
- Uses `pageSize=100` by default.
- Reuses one HTTP session per command execution.
- Retries failed or empty pages up to 3 times by default.
- Saves intermediate CSV chunks and checkpoint every 100 pages.
- Prints progress every page by default.
- Fetches pages sequentially by default, with optional conservative parallel workers.
- Supports `--resume` using the checkpoint and partial CSV.
- Skips already completed periods when checkpoint and CSV counts match.
- Writes ETL-style run logs with start time, end time, success flag, expected count, collected count, output file, and error message.

## Dataset Layout

New monthly collection output is stored under `dataset/work24/monthly` by default.

```text
dataset/
  work24/
    monthly/
      국민내일배움카드/
        국민내일배움카드훈련과정_202606.csv
      사업주훈련/
        사업주훈련_202606.csv
      국가인적자원개발 컨소시엄/
        국가인적자원개발 컨소시엄_202606.csv
      일학습병행/
        일학습병행_202606.csv
```

Power BI-friendly yearly merge output is stored under `dataset/work24/yearly`.

```text
dataset/
  work24/
    yearly/
      국민내일배움카드/
        국민내일배움카드훈련과정_2026.csv
      사업주훈련/
        사업주훈련_2026.csv
      국가인적자원개발 컨소시엄/
        국가인적자원개발 컨소시엄_2026.csv
      일학습병행/
        일학습병행_2026.csv
```

The yearly merge reads only monthly files that match `API name_YYYYMM.csv`.
Older files such as `YYYY년도_총...csv` are ignored.

Before merging, the script checks checkpoint `expected_count` against the monthly CSV row count.
If a monthly file is incomplete, the merge stops unless `--allow-incomplete` is explicitly passed.

Examples:

```powershell
python script\yearly_csv_merge.py --api national-card --year 2024 --overwrite
python script\yearly_csv_merge.py --api non-national-card --year 2024 --overwrite
python script\yearly_csv_merge.py --api all --overwrite
```

Existing files in the old `dataset/<API name>/...` locations are not moved by this script.

You can override the destination with `--output-dir`.

Resume uses the CSV path implied by the current `--output-dir`. If you want to resume older runs saved directly under `dataset/<API name>/...`, pass the old output root explicitly:

```powershell
python script\monthly_api_collection.py --api national-card --start 20240101 --end 20240131 --output-dir dataset --simple-filename --resume
```

When a completed period is skipped, the terminal prints:

```text
Already complete [국민내일배움카드훈련과정 20240601-20240630] rows=84248/84248, next_page=844, skip
```

## Progress Log Frequency

By default, progress is printed every page to preserve the original behavior.

To reduce terminal output, use `--progress-every-pages`.

Example:

```powershell
python script\monthly_api_collection.py --api national-card --start 20240601 --end 20241231 --simple-filename --resume --progress-every-pages 10
```

This prints normal page progress every 10 pages. Intermediate save logs are still printed whenever data is saved.

## Conservative Parallel Fetch

By default, `--workers` is `1`, so pages are fetched sequentially.

To enable conservative parallel fetching, use `--workers 2`.

Example:

```powershell
python script\monthly_api_collection.py --api national-card --start 20240601 --end 20241231 --simple-filename --resume --workers 2 --progress-every-pages 10
```

The collector fetches pages in parallel within each save block, then sorts results by page number before appending to CSV.

For a two-terminal backfill, keep date ranges non-overlapping per API and run the larger API separately:

```powershell
# Terminal 1
python script\monthly_api_collection.py --api national-card --start 20240101 --end 20241231 --simple-filename --resume --workers 3 --progress-every-pages 10

# Terminal 2
python script\monthly_api_collection.py --api non-national-card --start 20240101 --end 20241231 --simple-filename --resume --workers 2 --progress-every-pages 10
```

Recommended values:

| Workers | Use case |
| --- | --- |
| `1` | Safest default. |
| `2` | Conservative speed-up. Recommended first parallel setting. |
| `3` | Moderate speed-up if API responses remain stable. |
| `4` | Current hard cap. Use only after testing. |

Values above `4` are rejected to avoid excessive API traffic.

## Intermediate Save Logs

Intermediate saves use chunk append. The first chunk creates or overwrites the CSV with a header, and later chunks append only newly collected rows.

Whenever intermediate data is saved, the terminal prints the chunk row count, total row count, next page, write mode, interval speed, average speed, CSV path, checkpoint path, and timestamp.

Example:

```text
Intermediate save [국민내일배움카드훈련과정 20240101-20240131] chunk_rows=10000, total_rows=10000/37880, next_page=101, mode=append, interval=42.8s, interval_rate=2.34 pages/s (234 rows/s), avg_rate=2.31 pages/s (231 rows/s), csv=dataset\work24\monthly\국민내일배움카드\국민내일배움카드훈련과정_202401.csv, checkpoint=logs\checkpoints\national-card_20240101_20240131.json, saved_at=2026-07-11T13:30:00
```

The checkpoint also stores elapsed seconds and average rates:

```json
{
  "elapsed_seconds": 42.812,
  "avg_rows_per_sec": 231.243,
  "avg_pages_per_sec": 2.336
}
```

If a run fails after collecting some rows, a failure checkpoint message is also printed:

```text
Failure checkpoint [국민내일배움카드훈련과정 20240101-20240131] rows=12000/37880, next_page=121, csv=dataset\work24\monthly\국민내일배움카드\국민내일배움카드훈련과정_202401.csv, checkpoint=logs\checkpoints\national-card_20240101_20240131.json, saved_at=2026-07-11T13:35:00, error=...
```

## Notes

- Raw API response columns are preserved in the CSV output.
- No SQLite loading is performed in this script.
- Daily rolling refresh is a policy/design decision; this script still receives explicit `--start` and `--end` dates.
- Existing notebooks are not modified.
- If the API expected count differs from collected row count, the run is marked as failed and the partial CSV/checkpoint are kept for investigation.
