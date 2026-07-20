"""CSV Warehouse ETL orchestration."""

from __future__ import annotations

import os
import sys
from dataclasses import replace
from datetime import datetime, timedelta
from time import perf_counter
from typing import Any

from csv_warehouse.cleanup import cleanup_old_checkpoints
from csv_warehouse.logging import write_data_snapshot_log, write_etl_log
from csv_warehouse.paths import warehouse_log_path
from csv_warehouse.publisher import merge_yearly_snapshots
from work24_collector.client import create_session
from work24_collector.collector import collect_period
from work24_collector.config import (
    API_COLLECTION_ORDER,
    API_SPECS,
    CollectorSettings,
    NON_NATIONAL_CARD_COLLECTION_ORDER,
)
from work24_collector.dates import month_ranges
from work24_collector.env import load_env_file


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


def collector_settings(args: Any, resume: bool) -> CollectorSettings:
    return CollectorSettings(
        output_dir=args.monthly_dir,
        checkpoint_dir=args.checkpoint_dir,
        log_path=warehouse_log_path(args.warehouse_dir, "api_collection_runs.csv"),
        page_size=args.page_size,
        timeout_seconds=args.timeout_seconds,
        max_retries=args.max_retries,
        retry_sleep_seconds=args.retry_sleep_seconds,
        save_every_pages=args.save_every_pages,
        progress_every_pages=args.progress_every_pages,
        workers=args.workers,
        encoding=args.encoding,
        resume=resume,
        simple_filename=True,
    )


def collect_period_with_retries(
    settings: CollectorSettings,
    session: Any,
    spec: Any,
    api_key: str,
    period_start: str,
    period_end: str,
    period_retries: int,
) -> dict[str, Any]:
    attempts = period_retries + 1
    last_error: Exception | None = None

    for attempt in range(1, attempts + 1):
        try:
            attempt_settings = settings if attempt == 1 else replace(settings, resume=False)
            if attempt > 1:
                print(
                    f"Retry period [{spec.display_name} {period_start}-{period_end}] "
                    f"attempt={attempt}/{attempts}"
                )
            return collect_period(attempt_settings, session, spec, api_key, period_start, period_end)
        except Exception as exc:
            last_error = exc
            if attempt >= attempts:
                break
            print(
                f"Period collection failed. Will retry from page 1 "
                f"[{spec.display_name} {period_start}-{period_end}] error={exc}"
            )

    assert last_error is not None
    raise last_error


def run_csv_warehouse_etl(args: Any) -> int:
    started_at = datetime.now()
    started_perf = perf_counter()
    etl_log_path = warehouse_log_path(args.warehouse_dir, "etl_log.csv")
    data_snapshot_log_path = warehouse_log_path(args.warehouse_dir, "data_snapshot_log.csv")
    run_id = datetime.now().strftime("%Y%m%d%H%M%S")
    is_resume_run = not args.fresh_run
    expected_count = 0
    actual_count = 0
    status = "FAIL"
    message = ""
    window_start = ""
    window_end = ""
    cleanup_message = ""

    try:
        load_env_file(args.env_file)
        as_of = args.as_of or datetime.now()
        start_dt, end_dt = refresh_window(as_of, args.months_back, args.months_forward)
        window_start = start_dt.strftime("%Y%m%d")
        window_end = end_dt.strftime("%Y%m%d")
        periods = month_ranges(start_dt, end_dt)
        api_codes = selected_api_codes(args.api)
        years = list(range(start_dt.year, end_dt.year + 1))
        settings = collector_settings(args, resume=is_resume_run)

        print(
            f"Run CSV Warehouse ETL run_id={run_id}, "
            f"window={start_dt:%Y%m%d}-{end_dt:%Y%m%d}, dataset=training_course, "
            f"resume={is_resume_run}, monthly_dir={args.monthly_dir}, yearly_dir={args.yearly_dir}"
        )

        with create_session() as session:
            for api_code in api_codes:
                spec = API_SPECS[api_code]
                api_key = os.environ.get(spec.key_env)
                if not api_key:
                    raise RuntimeError(f"Missing API key. Set {spec.key_env} in environment or {args.env_file}.")
                for period_start, period_end in periods:
                    result = collect_period_with_retries(
                        settings,
                        session,
                        spec,
                        api_key,
                        period_start,
                        period_end,
                        args.period_retries,
                    )
                    expected_count += int(result.get("expected_count", 0))
                    actual_count += int(result.get("collected_count", 0))

        snapshots = merge_yearly_snapshots(
            api_codes,
            years,
            args.monthly_dir,
            args.yearly_dir,
            args.checkpoint_dir,
            args.encoding,
        )
        write_data_snapshot_log(data_snapshot_log_path, run_id, datetime.now(), snapshots)
        changed_count = sum(1 for snapshot in snapshots if snapshot.is_changed)
        status = "PASS"
        if expected_count != actual_count:
            message = (
                f"PASS with warning: expected_hint({expected_count})와 "
                f"actual_count({actual_count})가 다릅니다.; "
                f"yearly_files={len(snapshots)}, changed_files={changed_count}"
            )
        else:
            message = (
                f"PASS: refreshed monthly CSV and yearly snapshots in {args.yearly_dir}; "
                f"yearly_files={len(snapshots)}, changed_files={changed_count}"
            )
        print(message)

        return 0
    except Exception as exc:
        message = str(exc)
        print(f"ETL failed. Keep existing yearly CSV snapshots. {message}", file=sys.stderr)
        return 1
    finally:
        finished_at = datetime.now()
        duration_seconds = round(perf_counter() - started_perf, 3)
        if not args.skip_cleanup:
            try:
                deleted_checkpoints = cleanup_old_checkpoints(
                    args.checkpoint_dir,
                    args.checkpoint_retention_days,
                    finished_at,
                )
                cleanup_message = (
                    f"cleanup: deleted_checkpoints={deleted_checkpoints}, "
                    f"checkpoint_retention_days={args.checkpoint_retention_days}"
                )
                print(cleanup_message)
            except Exception as exc:
                cleanup_message = f"cleanup failed: {exc}"
                print(cleanup_message, file=sys.stderr)
        elif args.skip_cleanup:
            cleanup_message = "cleanup skipped"

        final_message = message
        if cleanup_message:
            final_message = f"{message}; {cleanup_message}" if message else cleanup_message
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
                "window_start": window_start,
                "window_end": window_end,
                "months_back": args.months_back,
                "months_forward": args.months_forward,
                "is_resume": is_resume_run,
                "duration_seconds": duration_seconds,
                "message": final_message,
            },
        )

