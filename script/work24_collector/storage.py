from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

import pandas as pd

from .config import ApiSpec


RUN_LOG_FIELDS = [
    "run_id",
    "api",
    "period_start",
    "period_end",
    "started_at",
    "ended_at",
    "success",
    "expected_count",
    "collected_count",
    "output_file",
    "error_message",
]


def checkpoint_path(checkpoint_dir: Path, spec: ApiSpec, start: str, end: str) -> Path:
    return checkpoint_dir / f"{spec.code}_{start}_{end}.json"


def save_checkpoint(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_checkpoint(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def output_file_path(output_root: Path, spec: ApiSpec, start: str, end: str, simple_name: bool) -> Path:
    output_dir = output_root / spec.output_dir_name
    output_dir.mkdir(parents=True, exist_ok=True)

    if simple_name and start[:6] == end[:6]:
        filename = f"{spec.display_name}_{start[:6]}.csv"
    else:
        filename = f"{spec.display_name}_{start}_{end}.csv"
    return output_dir / filename


def save_csv(rows: list[dict[str, Any]], path: Path, encoding: str) -> None:
    pd.DataFrame(rows).to_csv(path, index=False, encoding=encoding)


def append_csv(rows: list[dict[str, Any]], path: Path, encoding: str, include_header: bool) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = "w" if include_header else "a"
    write_encoding = encoding
    if not include_header and encoding.lower().replace("_", "-") == "utf-8-sig":
        write_encoding = "utf-8"
    pd.DataFrame(rows).to_csv(path, index=False, encoding=write_encoding, mode=mode, header=include_header)


def count_csv_rows(path: Path, encoding: str) -> int:
    if not path.exists():
        return 0

    count = 0
    for chunk in pd.read_csv(path, low_memory=False, chunksize=100_000, encoding=encoding):
        count += len(chunk)
    return count


def write_run_log(log_path: Path, row: dict[str, Any]) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    exists = log_path.exists()
    with log_path.open("a", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=RUN_LOG_FIELDS)
        if not exists:
            writer.writeheader()
        writer.writerow({field: row.get(field, "") for field in RUN_LOG_FIELDS})
