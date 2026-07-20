"""CSV log writers for ETL and data snapshot logs."""

from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
from typing import Any

from csv_warehouse.snapshot import DataSnapshot


ETL_LOG_FIELDS = [
    "run_id",
    "started_at",
    "finished_at",
    "dataset",
    "status",
    "expected_count",
    "actual_count",
    "window_start",
    "window_end",
    "months_back",
    "months_forward",
    "is_resume",
    "duration_seconds",
    "message",
]

DATA_SNAPSHOT_LOG_FIELDS = [
    "run_id",
    "created_at",
    "dataset",
    "api",
    "year",
    "file_path",
    "row_count",
    "file_size_bytes",
    "checksum",
    "previous_checksum",
    "is_changed",
    "message",
]


def write_etl_log(log_path: Path, row: dict[str, Any]) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    exists = log_path.exists()
    if exists:
        ensure_log_header(log_path, ETL_LOG_FIELDS)
    with log_path.open("a", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=ETL_LOG_FIELDS)
        if not exists:
            writer.writeheader()
        writer.writerow({field: row.get(field, "") for field in ETL_LOG_FIELDS})


def write_data_snapshot_log(log_path: Path, run_id: str, created_at: datetime, snapshots: list[DataSnapshot]) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    exists = log_path.exists()
    if exists:
        ensure_log_header(log_path, DATA_SNAPSHOT_LOG_FIELDS)
    with log_path.open("a", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=DATA_SNAPSHOT_LOG_FIELDS)
        if not exists:
            writer.writeheader()
        for snapshot in snapshots:
            writer.writerow(
                {
                    "run_id": run_id,
                    "created_at": created_at.isoformat(timespec="seconds"),
                    "dataset": "training_course",
                    "api": snapshot.api,
                    "year": snapshot.year,
                    "file_path": str(snapshot.file_path),
                    "row_count": snapshot.row_count,
                    "file_size_bytes": snapshot.file_size_bytes,
                    "checksum": snapshot.checksum,
                    "previous_checksum": snapshot.previous_checksum,
                    "is_changed": "Y" if snapshot.is_changed else "N",
                    "message": snapshot.message,
                }
            )


def ensure_log_header(log_path: Path, fields: list[str]) -> None:
    with log_path.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        existing_fields = reader.fieldnames or []
        if existing_fields == fields:
            return
        rows = list(reader)

    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})

