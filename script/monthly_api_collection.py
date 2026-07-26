"""Command-line entry point for monthly Work24 API collection."""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path

from work24_collector.client import create_session
from work24_collector.collector import collect_period
from work24_collector.config import (
    API_COLLECTION_ORDER,
    API_SPECS,
    DEFAULT_MAX_RETRIES,
    DEFAULT_PAGE_SIZE,
    DEFAULT_PROGRESS_EVERY_PAGES,
    DEFAULT_RETRY_SLEEP_SECONDS,
    DEFAULT_SAVE_EVERY_PAGES,
    DEFAULT_TIMEOUT_SECONDS,
    DEFAULT_WORKERS,
    MAX_WORKERS,
    NON_NATIONAL_CARD_COLLECTION_ORDER,
    CollectorSettings,
)
from work24_collector.dates import month_ranges, parse_yyyymmdd
from work24_collector.env import load_env_file


def parse_args(argv: list[str]) -> argparse.Namespace:
    class HelpFormatter(argparse.ArgumentDefaultsHelpFormatter, argparse.RawDescriptionHelpFormatter):
        pass

    parser = argparse.ArgumentParser(
        description="Collect monthly Work24 training-course API data as CSV.",
        formatter_class=HelpFormatter,
        epilog="""Examples:
  python script\\monthly_api_collection.py --api national-card --start 20240101 --end 20241231 --simple-filename --resume
  python script\\monthly_api_collection.py --api non-national-card --start 20240601 --end 20240630 --simple-filename --resume --workers 2
""",
    )
    parser.add_argument(
        "--api",
        choices=["all", "non-national-card", *API_COLLECTION_ORDER],
        required=True,
        help="API to collect. Use 'all' for every API, or 'non-national-card' for the three smaller APIs.",
    )
    parser.add_argument("--start", type=parse_yyyymmdd, required=True, help="Start date in YYYYMMDD.")
    parser.add_argument("--end", type=parse_yyyymmdd, required=True, help="End date in YYYYMMDD.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("dataset/work24/monthly"),
        help="Output root directory. API-specific folders are created below this path.",
    )
    parser.add_argument(
        "--checkpoint-dir",
        type=Path,
        default=Path("warehouse/checkpoints"),
        help="Checkpoint directory.",
    )
    parser.add_argument(
        "--log-path",
        type=Path,
        default=Path("warehouse/logs/api_collection_runs.csv"),
        help="Run log CSV path.",
    )
    parser.add_argument("--env-file", type=Path, default=Path(".env"), help="Environment file containing API keys.")
    parser.add_argument(
        "--page-size",
        type=int,
        default=DEFAULT_PAGE_SIZE,
        help=f"Rows per API page. Valid range: 1-{DEFAULT_PAGE_SIZE}.",
    )
    parser.add_argument("--timeout-seconds", type=int, default=DEFAULT_TIMEOUT_SECONDS, help="HTTP timeout per request.")
    parser.add_argument(
        "--max-retries",
        type=int,
        default=DEFAULT_MAX_RETRIES,
        help="Retry attempts per page request. Valid range: 1 or more.",
    )
    parser.add_argument(
        "--retry-sleep-seconds",
        type=float,
        default=DEFAULT_RETRY_SLEEP_SECONDS,
        help="Base sleep seconds between retries. Actual sleep increases by attempt number.",
    )
    parser.add_argument(
        "--save-every-pages",
        type=int,
        default=DEFAULT_SAVE_EVERY_PAGES,
        help="Append CSV and checkpoint every N pages. Valid range: 1 or more.",
    )
    parser.add_argument(
        "--progress-every-pages",
        type=int,
        default=DEFAULT_PROGRESS_EVERY_PAGES,
        help="Print progress every N pages. Valid range: 1 or more.",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=DEFAULT_WORKERS,
        help=f"Number of parallel page fetch workers. Valid range: 1-{MAX_WORKERS}.",
    )
    parser.add_argument("--encoding", default="utf-8-sig", help="CSV encoding.")
    parser.add_argument("--resume", action="store_true", help="Resume from checkpoint if present.")
    parser.add_argument("--simple-filename", action="store_true", help="Use API_YYYYMM.csv for monthly output.")
    return parser.parse_args(argv)


def settings_from_args(args: argparse.Namespace) -> CollectorSettings:
    return CollectorSettings(
        output_dir=args.output_dir,
        checkpoint_dir=args.checkpoint_dir,
        log_path=args.log_path,
        page_size=args.page_size,
        timeout_seconds=args.timeout_seconds,
        max_retries=args.max_retries,
        retry_sleep_seconds=args.retry_sleep_seconds,
        save_every_pages=args.save_every_pages,
        progress_every_pages=args.progress_every_pages,
        workers=args.workers,
        encoding=args.encoding,
        resume=args.resume,
        simple_filename=args.simple_filename,
        run_mode="resume" if args.resume else "scheduled",
        collection_refresh_days=7,
        collection_date=datetime.now().strftime("%Y%m%d"),
        etl_run_id="",
    )


def validate_args(args: argparse.Namespace) -> str | None:
    if args.page_size <= 0:
        return "--page-size must be greater than 0."
    if args.page_size > DEFAULT_PAGE_SIZE:
        return f"--page-size is capped at {DEFAULT_PAGE_SIZE} by the Work24 API."
    if args.save_every_pages <= 0:
        return "--save-every-pages must be greater than 0."
    if args.max_retries <= 0:
        return "--max-retries must be greater than 0."
    if args.progress_every_pages <= 0:
        return "--progress-every-pages must be greater than 0."
    if args.workers <= 0:
        return "--workers must be greater than 0."
    if args.workers > MAX_WORKERS:
        return f"--workers is capped at {MAX_WORKERS} for conservative API usage."
    return None


def selected_api_codes(api: str) -> list[str]:
    if api == "all":
        return list(API_COLLECTION_ORDER)
    if api == "non-national-card":
        return list(NON_NATIONAL_CARD_COLLECTION_ORDER)
    return [api]


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    error = validate_args(args)
    if error:
        print(error, file=sys.stderr)
        return 2

    load_env_file(args.env_file)

    settings = settings_from_args(args)
    with create_session() as session:
        for api_code in selected_api_codes(args.api):
            spec = API_SPECS[api_code]
            api_key = os.environ.get(spec.key_env)
            if not api_key:
                print(f"Missing API key. Set {spec.key_env} in environment or {args.env_file}.", file=sys.stderr)
                return 2

            print(f"=== Start API: {spec.display_name} ({spec.code}) ===")
            for start, end in month_ranges(args.start, args.end):
                collect_period(settings, session, spec, api_key, start, end)
            print(f"=== Finished API: {spec.display_name} ({spec.code}) ===")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
