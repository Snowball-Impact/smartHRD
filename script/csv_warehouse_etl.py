"""Publish Work24 API data into a CSV Warehouse current file.

The demo pipeline keeps CSV as the warehouse storage layer:

Extract -> Validate -> Publish -> Logging
"""

from __future__ import annotations

import argparse
import csv
import os
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from time import perf_counter
from typing import Any

import pandas as pd

from work24_collector.client import create_session
from work24_collector.collector import collect_period
from work24_collector.config import (
    API_COLLECTION_ORDER,
    API_SPECS,
    DEFAULT_MAX_RETRIES,
    DEFAULT_PAGE_SIZE,
    DEFAULT_RETRY_SLEEP_SECONDS,
    DEFAULT_TIMEOUT_SECONDS,
    MAX_WORKERS,
    NON_NATIONAL_CARD_COLLECTION_ORDER,
    CollectorSettings,
)
from work24_collector.dates import month_ranges, parse_yyyymmdd
from work24_collector.env import load_env_file


ETL_LOG_FIELDS = [
    "run_id",
    "started_at",
    "finished_at",
    "dataset",
    "status",
    "expected_count",
    "actual_count",
    "duration_seconds",
    "message",
]

REQUIRED_COLUMNS = [
    "trprId",
    "trprDegr",
    "trainstCstId",
    "traStartDate",
    "traEndDate",
]

DEDUP_KEY = [
    "source_api",
    "trprId",
    "trprDegr",
    "trainstCstId",
    "traStartDate",
    "traEndDate",
]


@dataclass(frozen=True)
class ValidationResult:
    passed: bool
    actual_count: int
    message: str


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the SmartHRD CSV Warehouse demo ETL.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--api", choices=["all", "non-national-card", *API_COLLECTION_ORDER], default="all")
    parser.add_argument("--as-of", type=parse_yyyymmdd, default=None, help="Base date in YYYYMMDD. Defaults to today.")
    parser.add_argument("--months-back", type=int, default=6, help="Months before the current month to collect.")
    parser.add_argument("--months-forward", type=int, default=6, help="Months after the current month to collect.")
    parser.add_argument("--warehouse-dir", type=Path, default=Path("warehouse"))
    parser.add_argument("--env-file", type=Path, default=Path(".env"))
    parser.add_argument("--page-size", type=int, default=DEFAULT_PAGE_SIZE)
    parser.add_argument("--timeout-seconds", type=int, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--max-retries", type=int, default=DEFAULT_MAX_RETRIES)
    parser.add_argument("--retry-sleep-seconds", type=float, default=DEFAULT_RETRY_SLEEP_SECONDS)
    parser.add_argument("--save-every-pages", type=int, default=100)
    parser.add_argument("--progress-every-pages", type=int, default=10)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--encoding", default="utf-8-sig")
    parser.add_argument("--keep-temp", action="store_true", help="Keep the run temp directory after success.")
    return parser.parse_args(argv)


def validate_args(args: argparse.Namespace) -> str | None:
    if args.months_back < 0 or args.months_forward < 0:
        return "--months-back and --months-forward must be 0 or greater."
    if args.page_size <= 0 or args.page_size > DEFAULT_PAGE_SIZE:
        return f"--page-size must be between 1 and {DEFAULT_PAGE_SIZE}."
    if args.max_retries <= 0:
        return "--max-retries must be greater than 0."
    if args.save_every_pages <= 0:
        return "--save-every-pages must be greater than 0."
    if args.progress_every_pages <= 0:
        return "--progress-every-pages must be greater than 0."
    if args.workers <= 0 or args.workers > MAX_WORKERS:
        return f"--workers must be between 1 and {MAX_WORKERS}."
    return None


def selected_api_codes(api: str) -> list[str]:
    if api == "all":
        return list(API_COLLECTION_ORDER)
    if api == "non-national-card":
        return list(NON_NATIONAL_CARD_COLLECTION_ORDER)
    return [api]


def add_months(value: datetime, months: int) -> datetime:
    month_index = value.year * 12 + value.month - 1 + months
    year = month_index // 12
    month = month_index % 12 + 1
    return datetime(year, month, 1)


def refresh_window(as_of: datetime, months_back: int, months_forward: int) -> tuple[datetime, datetime]:
    current_month = datetime(as_of.year, as_of.month, 1)
    start = add_months(current_month, -months_back)
    after_end_month = add_months(current_month, months_forward + 1)
    end = after_end_month - timedelta(days=1)
    return start, end


def collector_settings(args: argparse.Namespace, run_dir: Path) -> CollectorSettings:
    return CollectorSettings(
        output_dir=run_dir / "monthly",
        checkpoint_dir=run_dir / "checkpoints",
        log_path=args.warehouse_dir / "logs" / "api_collection_runs.csv",
        page_size=args.page_size,
        timeout_seconds=args.timeout_seconds,
        max_retries=args.max_retries,
        retry_sleep_seconds=args.retry_sleep_seconds,
        save_every_pages=args.save_every_pages,
        progress_every_pages=args.progress_every_pages,
        workers=args.workers,
        encoding=args.encoding,
        resume=False,
        simple_filename=True,
    )


def merge_monthly_outputs(run_dir: Path, api_codes: list[str], output_path: Path, encoding: str) -> int:
    total_rows = 0
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists():
        output_path.unlink()

    wrote_header = False
    for api_code in api_codes:
        spec = API_SPECS[api_code]
        input_dir = run_dir / "monthly" / spec.output_dir_name
        for input_path in sorted(input_dir.glob(f"{spec.display_name}_*.csv")):
            period = input_path.stem.rsplit("_", 1)[-1]
            for chunk in pd.read_csv(input_path, dtype=str, encoding=encoding, chunksize=100_000):
                chunk.insert(0, "source_api", spec.code)
                chunk.insert(1, "source_dataset", spec.display_name)
                chunk.insert(2, "source_period", period)
                chunk.to_csv(
                    output_path,
                    index=False,
                    encoding=encoding if not wrote_header else "utf-8",
                    mode="w" if not wrote_header else "a",
                    header=not wrote_header,
                )
                wrote_header = True
                total_rows += len(chunk)
    return total_rows


def validate_tmp_csv(path: Path, expected_count: int, encoding: str) -> ValidationResult:
    if not path.exists():
        return ValidationResult(False, 0, f"CSV 저장 실패: {path} 파일이 없습니다.")

    actual_count = 0
    duplicate_count = 0
    null_counts = {column: 0 for column in REQUIRED_COLUMNS}
    missing_required: list[str] = []
    seen_keys: set[tuple[str, ...]] = set()

    try:
        for chunk in pd.read_csv(path, dtype=str, encoding=encoding, chunksize=100_000):
            actual_count += len(chunk)
            if not missing_required:
                missing_required = [column for column in REQUIRED_COLUMNS if column not in chunk.columns]
            if missing_required:
                continue

            for column in REQUIRED_COLUMNS:
                null_counts[column] += int((chunk[column].fillna("").str.strip() == "").sum())

            for key in chunk[DEDUP_KEY].fillna("").itertuples(index=False, name=None):
                key_tuple = tuple(str(value).strip() for value in key)
                if key_tuple in seen_keys:
                    duplicate_count += 1
                else:
                    seen_keys.add(key_tuple)
    except Exception as exc:
        return ValidationResult(False, actual_count, f"CSV 읽기/검증 실패: {exc}")

    if expected_count != actual_count:
        return ValidationResult(False, actual_count, f"예상 건수({expected_count})와 실제 건수({actual_count})가 다릅니다.")
    if missing_required:
        return ValidationResult(False, actual_count, f"필수 컬럼 누락: {', '.join(missing_required)}")

    failed_nulls = {column: count for column, count in null_counts.items() if count > 0}
    if failed_nulls:
        detail = ", ".join(f"{column}={count}" for column, count in failed_nulls.items())
        return ValidationResult(False, actual_count, f"필수 컬럼 NULL/빈값 발견: {detail}")
    if duplicate_count:
        return ValidationResult(False, actual_count, f"중복 row identity 발견: {duplicate_count}건")

    return ValidationResult(True, actual_count, "PASS")


def publish_current(tmp_path: Path, current_path: Path, backup_dir: Path, run_id: str) -> None:
    current_path.parent.mkdir(parents=True, exist_ok=True)
    backup_dir.mkdir(parents=True, exist_ok=True)
    if current_path.exists():
        backup_path = backup_dir / f"{current_path.stem}_{run_id}{current_path.suffix}"
        shutil.copy2(current_path, backup_path)
    shutil.move(str(tmp_path), str(current_path))


def write_etl_log(log_path: Path, row: dict[str, Any]) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    exists = log_path.exists()
    with log_path.open("a", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=ETL_LOG_FIELDS)
        if not exists:
            writer.writeheader()
        writer.writerow({field: row.get(field, "") for field in ETL_LOG_FIELDS})


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    error = validate_args(args)
    if error:
        print(error, file=sys.stderr)
        return 2

    run_id = datetime.now().strftime("%Y%m%d%H%M%S")
    started_at = datetime.now()
    started_perf = perf_counter()
    run_dir = args.warehouse_dir / "tmp" / run_id
    tmp_csv = run_dir / "training_course.tmp.csv"
    current_csv = args.warehouse_dir / "current" / "training_course.csv"
    backup_dir = args.warehouse_dir / "backup"
    etl_log_path = args.warehouse_dir / "logs" / "etl_log.csv"
    expected_count = 0
    actual_count = 0
    status = "FAIL"
    message = ""

    try:
        load_env_file(args.env_file)
        as_of = args.as_of or datetime.now()
        start_dt, end_dt = refresh_window(as_of, args.months_back, args.months_forward)
        periods = month_ranges(start_dt, end_dt)
        api_codes = selected_api_codes(args.api)
        settings = collector_settings(args, run_dir)

        print(
            f"Run CSV Warehouse ETL run_id={run_id}, "
            f"window={start_dt:%Y%m%d}-{end_dt:%Y%m%d}, dataset=training_course"
        )

        with create_session() as session:
            for api_code in api_codes:
                spec = API_SPECS[api_code]
                api_key = os.environ.get(spec.key_env)
                if not api_key:
                    raise RuntimeError(f"Missing API key. Set {spec.key_env} in environment or {args.env_file}.")
                for period_start, period_end in periods:
                    result = collect_period(settings, session, spec, api_key, period_start, period_end)
                    expected_count += int(result.get("expected_count", 0))

        actual_count = merge_monthly_outputs(run_dir, api_codes, tmp_csv, args.encoding)
        validation = validate_tmp_csv(tmp_csv, expected_count, args.encoding)
        actual_count = validation.actual_count
        message = validation.message

        if validation.passed:
            publish_current(tmp_csv, current_csv, backup_dir, run_id)
            status = "PASS"
            message = f"PASS: published {current_csv}"
            print(message)
        else:
            print(f"Validation failed. Keep existing current CSV. {message}", file=sys.stderr)
            return 1

        return 0
    except Exception as exc:
        message = str(exc)
        print(f"ETL failed. Keep existing current CSV. {message}", file=sys.stderr)
        return 1
    finally:
        finished_at = datetime.now()
        duration_seconds = round(perf_counter() - started_perf, 3)
        write_etl_log(
            etl_log_path,
            {
                "run_id": run_id,
                "started_at": started_at.isoformat(timespec="seconds"),
                "finished_at": finished_at.isoformat(timespec="seconds"),
                "dataset": "training_course",
                "status": status,
                "expected_count": expected_count,
                "actual_count": actual_count,
                "duration_seconds": duration_seconds,
                "message": message,
            },
        )
        if status == "PASS" and not args.keep_temp and run_dir.exists():
            shutil.rmtree(run_dir)


if __name__ == "__main__":
    raise SystemExit(main())
