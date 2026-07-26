from __future__ import annotations

import math
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from time import perf_counter
from typing import Any

import requests

from .client import fetch_page, fetch_page_with_thread_session
from .config import ApiSpec, CollectionError, CollectorSettings
from .storage import (
    append_csv,
    checkpoint_path,
    count_csv_rows,
    load_checkpoint,
    output_file_path,
    save_checkpoint,
    write_run_log,
)


def collect_period(
    settings: CollectorSettings,
    session: requests.Session,
    spec: ApiSpec,
    api_key: str,
    start: str,
    end: str,
) -> dict[str, Any]:
    collection_run_id = f"{spec.code}_{start}_{end}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    cp_path = checkpoint_path(settings.checkpoint_dir, spec, start, end)
    out_path = output_file_path(settings.output_dir, spec, start, end, settings.simple_filename)
    log_row: dict[str, Any] = {
        "run_id": settings.etl_run_id or collection_run_id,
        "collection_run_id": collection_run_id,
        "api": spec.code,
        "period_start": start,
        "period_end": end,
        "started_at": datetime.now().isoformat(timespec="seconds"),
        "output_file": str(out_path),
    }

    pending_rows: list[dict[str, Any]] = []
    collected_count = 0
    expected_count = 0
    next_page = 1
    last_page_row_count = 0
    csv_has_header = False
    started_perf = perf_counter()
    last_save_perf = started_perf
    last_saved_count = collected_count
    last_saved_page = 0

    try:
        if settings.resume:
            checkpoint = load_checkpoint(cp_path)
            if checkpoint:
                expected_count = int(checkpoint.get("expected_count", 0))
                next_page = int(checkpoint.get("next_page", 1))
                collected_count = count_csv_rows(out_path, settings.encoding)
                checkpoint_count = int(checkpoint.get("collected_count", 0))
                csv_has_header = collected_count > 0
                last_saved_count = collected_count
                last_saved_page = max(next_page - 1, 0)
                print(f"Resume {spec.display_name} {start}-{end}: page {next_page}, rows {collected_count}")
                total_pages = math.ceil(expected_count / settings.page_size) if expected_count else 0
                legacy_complete = (
                    expected_count
                    and collected_count == expected_count
                    and checkpoint_count == expected_count
                    and total_pages
                    and next_page > total_pages
                )
                should_recollect_completed = (
                    settings.run_mode == "auto"
                    and (checkpoint.get("completed") or legacy_complete)
                    and is_checkpoint_stale(checkpoint, settings.collection_date, settings.collection_refresh_days)
                )
                if should_recollect_completed:
                    print(
                        "Completed checkpoint is old enough for scheduled recollection. "
                        f"[{spec.display_name} {start}-{end}] "
                        f"checkpoint_collection_date={checkpoint_collection_date(checkpoint) or 'unknown'}, "
                        f"current_collection_date={settings.collection_date}, "
                        f"refresh_days={settings.collection_refresh_days}. Restarting from page 1."
                    )
                    expected_count = 0
                    collected_count = 0
                    next_page = 1
                    csv_has_header = False
                    last_saved_count = 0
                    last_saved_page = 0
                    last_page_row_count = 0
                    checkpoint = None
                    log_row["skipped"] = False
                elif (checkpoint.get("completed") and collected_count == checkpoint_count) or legacy_complete:
                    print(
                        "Already complete "
                        f"[{spec.display_name} {start}-{end}] "
                        f"rows={collected_count}, expected_hint={expected_count}, skip"
                    )
                    if legacy_complete and not checkpoint.get("completed"):
                        save_completed_checkpoint(
                            cp_path,
                            out_path,
                            settings,
                            spec,
                            start,
                            end,
                            expected_count,
                            next_page,
                            collected_count,
                        )
                    log_row["skipped"] = True
                    log_success(settings, log_row, expected_count, collected_count)
                    return log_row
                if next_page > 1 and collected_count != checkpoint_count:
                    print(
                        "Checkpoint and CSV row count do not match. "
                        f"checkpoint={checkpoint_count}, csv={collected_count}. Restarting from page 1."
                    )
                    expected_count = 0
                    collected_count = 0
                    next_page = 1
                    csv_has_header = False
                    last_saved_count = 0
                    last_saved_page = 0
                elif next_page > 1 and collected_count == 0:
                    print("Checkpoint exists but partial CSV is missing. Restarting from page 1.")
                    expected_count = 0
                    collected_count = 0
                    next_page = 1
                    csv_has_header = False
                    last_saved_count = 0
                    last_saved_page = 0
                elif expected_count and collected_count != expected_count:
                    total_pages = math.ceil(expected_count / settings.page_size)
                    if next_page > total_pages:
                        print(
                            "Checkpoint reached the last page but collected row count is incomplete. "
                            f"expected={expected_count}, csv={collected_count}. Restarting from page 1."
                        )
                        expected_count = 0
                        collected_count = 0
                        next_page = 1
                        csv_has_header = False
                        last_saved_count = 0
                        last_saved_page = 0

        if next_page == 1:
            pending_rows, expected_count, next_page = collect_first_page(
                settings,
                session,
                spec,
                api_key,
                start,
                end,
            )
            collected_count += len(pending_rows)
            current_perf = perf_counter()
            last_save_perf, last_saved_count, last_saved_page = save_progress(
                cp_path,
                out_path,
                settings,
                spec,
                start,
                end,
                expected_count,
                next_page,
                collected_count,
                pending_rows,
                include_header=True,
                started_perf=started_perf,
                previous_save_perf=last_save_perf,
                previous_saved_count=last_saved_count,
                previous_saved_page=last_saved_page,
                current_page=1,
                current_perf=current_perf,
            )
            last_page_row_count = len(pending_rows)
            pending_rows = []
            csv_has_header = True

        total_pages_hint = math.ceil(expected_count / settings.page_size) if expected_count else 0
        print(f"Collect {spec.display_name} {start}-{end}: expected_hint {expected_count}, pages_hint {total_pages_hint}")

        while last_page_row_count >= settings.page_size:
            if total_pages_hint and next_page <= total_pages_hint:
                block_end_page = next_save_boundary(next_page, total_pages_hint, settings.save_every_pages)
            else:
                block_end_page = next_page
            page_results = collect_page_block(
                settings,
                session,
                spec,
                api_key,
                start,
                end,
                next_page,
                block_end_page,
            )

            for page_num, page_rows in page_results:
                pending_rows.extend(page_rows)
                collected_count += len(page_rows)
                last_page_row_count = len(page_rows)
                if should_print_progress(settings, page_num, total_pages_hint):
                    print(f"Page {page_num}/{total_pages_hint or '?'}: total rows {collected_count}")

            current_perf = perf_counter()
            last_save_perf, last_saved_count, last_saved_page = save_progress(
                cp_path,
                out_path,
                settings,
                spec,
                start,
                end,
                expected_count,
                block_end_page + 1,
                collected_count,
                pending_rows,
                include_header=not csv_has_header,
                started_perf=started_perf,
                previous_save_perf=last_save_perf,
                previous_saved_count=last_saved_count,
                previous_saved_page=last_saved_page,
                current_page=block_end_page,
                current_perf=current_perf,
            )
            pending_rows = []
            csv_has_header = True
            next_page = block_end_page + 1
            if total_pages_hint and block_end_page >= total_pages_hint and collected_count == expected_count:
                break

        if expected_count != collected_count:
            print(
                "Count warning "
                f"[{spec.display_name} {start}-{end}] "
                f"collected={collected_count}, expected_hint={expected_count}. "
                "Using collected rows because API page traversal reached the final short page."
            )

        save_completed_checkpoint(cp_path, out_path, settings, spec, start, end, expected_count, next_page, collected_count)
        log_row["skipped"] = False
        log_success(settings, log_row, expected_count, collected_count)
        print(f"Saved {collected_count} rows: {out_path}")
        return log_row

    except Exception as exc:
        failure_next_page = max(next_page, 1)
        if pending_rows:
            append_csv(pending_rows, out_path, settings.encoding, include_header=not csv_has_header)
            csv_has_header = True
            print(f"Partial chunk append: rows={len(pending_rows)}, csv={out_path}")
            failure_next_page = max(next_page + 1, 1)
        log_failure(settings, log_row, expected_count, collected_count, exc)
        save_failure_checkpoint(
            cp_path,
            out_path,
            settings,
            spec,
            start,
            end,
            expected_count,
            failure_next_page,
            collected_count,
            exc,
        )
        raise


def collect_first_page(
    settings: CollectorSettings,
    session: requests.Session,
    spec: ApiSpec,
    api_key: str,
    start: str,
    end: str,
) -> tuple[list[dict[str, Any]], int, int]:
    payload = fetch_page(
        session,
        spec,
        api_key,
        start,
        end,
        1,
        settings.page_size,
        settings.timeout_seconds,
        settings.max_retries,
        settings.retry_sleep_seconds,
    )
    expected_count = int(payload.get("scn_cnt", 0))
    return extract_rows(payload), expected_count, 2


def collect_page(
    settings: CollectorSettings,
    session: requests.Session,
    spec: ApiSpec,
    api_key: str,
    start: str,
    end: str,
    page_num: int,
) -> list[dict[str, Any]]:
    payload = fetch_page(
        session,
        spec,
        api_key,
        start,
        end,
        page_num,
        settings.page_size,
        settings.timeout_seconds,
        settings.max_retries,
        settings.retry_sleep_seconds,
    )
    return extract_rows(payload)


def collect_page_block(
    settings: CollectorSettings,
    session: requests.Session,
    spec: ApiSpec,
    api_key: str,
    start: str,
    end: str,
    start_page: int,
    end_page: int,
) -> list[tuple[int, list[dict[str, Any]]]]:
    page_numbers = list(range(start_page, end_page + 1))
    if settings.workers == 1 or len(page_numbers) == 1:
        return [
            (page_num, collect_page(settings, session, spec, api_key, start, end, page_num))
            for page_num in page_numbers
        ]

    print(f"Parallel fetch pages {start_page}-{end_page} with workers={settings.workers}")
    results: dict[int, list[dict[str, Any]]] = {}
    with ThreadPoolExecutor(max_workers=settings.workers) as executor:
        future_to_page = {
            executor.submit(collect_page_threaded, settings, spec, api_key, start, end, page_num): page_num
            for page_num in page_numbers
        }
        for future in as_completed(future_to_page):
            page_num = future_to_page[future]
            results[page_num] = future.result()

    return [(page_num, results[page_num]) for page_num in page_numbers]


def collect_page_threaded(
    settings: CollectorSettings,
    spec: ApiSpec,
    api_key: str,
    start: str,
    end: str,
    page_num: int,
) -> list[dict[str, Any]]:
    payload = fetch_page_with_thread_session(
        spec,
        api_key,
        start,
        end,
        page_num,
        settings.page_size,
        settings.timeout_seconds,
        settings.max_retries,
        settings.retry_sleep_seconds,
    )
    return extract_rows(payload)


def next_save_boundary(current_page: int, total_pages: int, save_every_pages: int) -> int:
    boundary = ((current_page - 1) // save_every_pages + 1) * save_every_pages
    return min(boundary, total_pages)


def should_print_progress(settings: CollectorSettings, page_num: int, total_pages: int) -> bool:
    return page_num % settings.progress_every_pages == 0 or page_num == total_pages


def extract_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows = payload.get("srchList", [])
    if not isinstance(rows, list):
        raise CollectionError("API response field srchList was not a list.")
    return rows


def save_progress(
    cp_path: Path,
    out_path: Path,
    settings: CollectorSettings,
    spec: ApiSpec,
    start: str,
    end: str,
    expected_count: int,
    next_page: int,
    collected_count: int,
    chunk_rows: list[dict[str, Any]],
    include_header: bool,
    started_perf: float,
    previous_save_perf: float,
    previous_saved_count: int,
    previous_saved_page: int,
    current_page: int,
    current_perf: float,
) -> tuple[float, int, int]:
    updated_at = datetime.now().isoformat(timespec="seconds")
    append_csv(chunk_rows, out_path, settings.encoding, include_header=include_header)
    interval_seconds = max(current_perf - previous_save_perf, 0.000001)
    total_seconds = max(current_perf - started_perf, 0.000001)
    interval_rows = max(collected_count - previous_saved_count, 0)
    interval_pages = max(current_page - previous_saved_page, 0)
    avg_rows_sec = collected_count / total_seconds
    avg_pages_sec = current_page / total_seconds
    interval_rows_sec = interval_rows / interval_seconds
    interval_pages_sec = interval_pages / interval_seconds
    save_checkpoint(
        cp_path,
        {
            "api": spec.code,
            "period_start": start,
            "period_end": end,
            "expected_count": expected_count,
            "next_page": next_page,
            "collected_count": collected_count,
            "output_file": str(out_path),
            "last_saved_rows": len(chunk_rows),
            "write_mode": "overwrite" if include_header else "append",
            "collection_date": settings.collection_date,
            "run_mode": settings.run_mode,
            "updated_at": updated_at,
            "elapsed_seconds": round(total_seconds, 3),
            "avg_rows_per_sec": round(avg_rows_sec, 3),
            "avg_pages_per_sec": round(avg_pages_sec, 3),
        },
    )
    print(
        "Intermediate save "
        f"[{spec.display_name} {start}-{end}] "
        f"chunk_rows={len(chunk_rows)}, total_rows={collected_count}/{expected_count}, "
        f"next_page={next_page}, mode={'overwrite' if include_header else 'append'}, "
        f"interval={interval_seconds:.1f}s, interval_rate={interval_pages_sec:.2f} pages/s "
        f"({interval_rows_sec:.0f} rows/s), avg_rate={avg_pages_sec:.2f} pages/s "
        f"({avg_rows_sec:.0f} rows/s), "
        f"csv={out_path}, checkpoint={cp_path}, saved_at={updated_at}"
    )
    return current_perf, collected_count, current_page


def save_failure_checkpoint(
    cp_path: Path,
    out_path: Path,
    settings: CollectorSettings,
    spec: ApiSpec,
    start: str,
    end: str,
    expected_count: int,
    next_page: int,
    collected_count: int,
    exc: Exception,
) -> None:
    updated_at = datetime.now().isoformat(timespec="seconds")
    save_checkpoint(
        cp_path,
        {
            "api": spec.code,
            "period_start": start,
            "period_end": end,
            "expected_count": expected_count,
            "next_page": next_page,
            "collected_count": collected_count,
            "output_file": str(out_path),
            "error_message": str(exc),
            "collection_date": settings.collection_date,
            "run_mode": settings.run_mode,
            "updated_at": updated_at,
        },
    )
    print(
        "Failure checkpoint "
        f"[{spec.display_name} {start}-{end}] "
        f"rows={collected_count}/{expected_count}, next_page={next_page}, "
        f"csv={out_path}, checkpoint={cp_path}, saved_at={updated_at}, error={exc}"
    )


def save_completed_checkpoint(
    cp_path: Path,
    out_path: Path,
    settings: CollectorSettings,
    spec: ApiSpec,
    start: str,
    end: str,
    expected_count: int,
    next_page: int,
    collected_count: int,
) -> None:
    updated_at = datetime.now().isoformat(timespec="seconds")
    save_checkpoint(
        cp_path,
        {
            "api": spec.code,
            "period_start": start,
            "period_end": end,
            "expected_count": expected_count,
            "next_page": next_page,
            "collected_count": collected_count,
            "output_file": str(out_path),
            "completed": True,
            "completion_rule": "final_short_page",
            "collected_at": updated_at,
            "collection_date": settings.collection_date,
            "run_mode": settings.run_mode,
            "updated_at": updated_at,
        },
    )


def checkpoint_collection_date(checkpoint: dict[str, Any]) -> str:
    return str(checkpoint.get("collection_date") or "")


def is_checkpoint_stale(checkpoint: dict[str, Any], collection_date: str, refresh_days: int) -> bool:
    previous_date = checkpoint_collection_date(checkpoint)
    if not previous_date:
        return True
    try:
        previous = datetime.strptime(previous_date, "%Y%m%d")
        current = datetime.strptime(collection_date, "%Y%m%d")
    except ValueError:
        return True
    return (current - previous).days >= refresh_days


def log_success(settings: CollectorSettings, log_row: dict[str, Any], expected_count: int, row_count: int) -> None:
    log_row.update(
        {
            "ended_at": datetime.now().isoformat(timespec="seconds"),
            "success": True,
            "expected_count": expected_count,
            "collected_count": row_count,
            "error_message": "",
        }
    )
    write_run_log(settings.log_path, log_row)


def log_failure(
    settings: CollectorSettings,
    log_row: dict[str, Any],
    expected_count: int,
    row_count: int,
    exc: Exception,
) -> None:
    log_row.update(
        {
            "ended_at": datetime.now().isoformat(timespec="seconds"),
            "success": False,
            "expected_count": expected_count,
            "collected_count": row_count,
            "error_message": str(exc),
        }
    )
    write_run_log(settings.log_path, log_row)
