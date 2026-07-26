"""Command-line entry point for the SmartHRD CSV Warehouse ETL."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from csv_warehouse.paths import (
    DEFAULT_CHECKPOINT_DIR,
    DEFAULT_ENV_FILE,
    DEFAULT_INTEGRATED_DIR,
    DEFAULT_MONTHLY_DIR,
    DEFAULT_WAREHOUSE_DIR,
    DEFAULT_YEARLY_DIR,
)
from csv_warehouse.pipeline import run_csv_warehouse_etl
from work24_collector.config import (
    API_COLLECTION_ORDER,
    DEFAULT_MAX_RETRIES,
    DEFAULT_PAGE_SIZE,
    DEFAULT_RETRY_SLEEP_SECONDS,
    DEFAULT_TIMEOUT_SECONDS,
    MAX_WORKERS,
)
from work24_collector.dates import parse_yyyymmdd


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the SmartHRD CSV Warehouse demo ETL.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--api", choices=["all", "non-national-card", *API_COLLECTION_ORDER], default="all")
    parser.add_argument("--as-of", type=parse_yyyymmdd, default=None, help="Base date in YYYYMMDD. Defaults to today.")
    parser.add_argument("--months-back", type=int, default=6, help="Months before the current month to collect.")
    parser.add_argument("--months-forward", type=int, default=6, help="Months after the current month to collect.")
    parser.add_argument("--warehouse-dir", type=Path, default=DEFAULT_WAREHOUSE_DIR)
    parser.add_argument("--monthly-dir", type=Path, default=DEFAULT_MONTHLY_DIR)
    parser.add_argument("--yearly-dir", type=Path, default=DEFAULT_YEARLY_DIR)
    parser.add_argument("--integrated-dir", type=Path, default=DEFAULT_INTEGRATED_DIR)
    parser.add_argument("--checkpoint-dir", type=Path, default=DEFAULT_CHECKPOINT_DIR)
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV_FILE)
    parser.add_argument(
        "--fresh-run",
        action="store_true",
        help="Deprecated alias for --run-mode scheduled.",
    )
    parser.add_argument(
        "--run-mode",
        choices=["auto", "scheduled", "resume"],
        default="auto",
        help=(
            "Collection mode. auto recollects completed periods when the checkpoint collection date "
            "is old enough, otherwise resumes/skips completed periods."
        ),
    )
    parser.add_argument(
        "--collection-refresh-days",
        type=int,
        default=7,
        help="In auto mode, recollect completed monthly files when the checkpoint collection date is this many days old.",
    )
    parser.add_argument(
        "--force-publish",
        action="store_true",
        help="Run yearly and integrated publish even when every monthly period was skipped.",
    )
    parser.add_argument("--page-size", type=int, default=DEFAULT_PAGE_SIZE)
    parser.add_argument("--timeout-seconds", type=int, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--max-retries", type=int, default=DEFAULT_MAX_RETRIES)
    parser.add_argument("--retry-sleep-seconds", type=float, default=DEFAULT_RETRY_SLEEP_SECONDS)
    parser.add_argument("--save-every-pages", type=int, default=100)
    parser.add_argument("--progress-every-pages", type=int, default=10)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument(
        "--period-retries",
        type=int,
        default=1,
        help="Retry a failed API/month collection from page 1 before failing the ETL.",
    )
    parser.add_argument("--encoding", default="utf-8-sig")
    parser.add_argument(
        "--checkpoint-retention-days",
        type=int,
        default=30,
        help="Delete checkpoint files older than this many days after the ETL finishes.",
    )
    parser.add_argument("--skip-cleanup", action="store_true", help="Skip post-run cleanup.")
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
    if args.period_retries < 0:
        return "--period-retries must be 0 or greater."
    if args.checkpoint_retention_days < 0:
        return "--checkpoint-retention-days must be 0 or greater."
    if args.collection_refresh_days < 0:
        return "--collection-refresh-days must be 0 or greater."
    return None


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    error = validate_args(args)
    if error:
        print(error, file=sys.stderr)
        return 2
    return run_csv_warehouse_etl(args)


if __name__ == "__main__":
    raise SystemExit(main())
