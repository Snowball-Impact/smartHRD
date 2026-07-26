"""Publish monthly Work24 CSV files into yearly and integrated snapshots."""

from __future__ import annotations

import re
import csv
from pathlib import Path

from csv_warehouse.snapshot import DataSnapshot, file_checksum
from work24_collector.config import API_SPECS, ApiSpec
from yearly_csv_merge import merge_monthly_files, monthly_files_for_year, validate_monthly_files, yearly_output_path


YEARLY_FILENAME_RE = re.compile(r"^(?P<name>.+)_(?P<year>\d{4})\.csv$")

def merge_yearly_snapshots(
    api_codes: list[str],
    years: list[int],
    monthly_dir: Path,
    yearly_dir: Path,
    checkpoint_dir: Path,
    encoding: str,
) -> list[DataSnapshot]:
    staged_outputs: list[tuple[Path, Path, DataSnapshot, int, str]] = []
    for api_code in api_codes:
        spec = API_SPECS[api_code]
        for year in years:
            files = monthly_files_for_year(monthly_dir, spec, year)
            if not files:
                continue
            output_path = yearly_output_path(yearly_dir, spec, year)
            temp_output_path = output_path.with_name(f"{output_path.stem}.tmp{output_path.suffix}")
            validate_monthly_files(files, spec, checkpoint_dir, encoding, allow_incomplete=False)
            row_count = merge_monthly_files(files, temp_output_path, encoding, overwrite=True)
            checksum = file_checksum(temp_output_path)
            previous_checksum = file_checksum(output_path) if output_path.exists() else ""
            is_changed = checksum != previous_checksum
            if not previous_checksum:
                snapshot_message = "FIRST_SNAPSHOT"
            elif is_changed:
                snapshot_message = "CHANGED"
            else:
                snapshot_message = "UNCHANGED"
            snapshot = DataSnapshot(
                api=spec.display_name,
                year=year,
                file_path=output_path,
                row_count=row_count,
                file_size_bytes=temp_output_path.stat().st_size,
                checksum=checksum,
                previous_checksum=previous_checksum,
                is_changed=is_changed,
                message=snapshot_message,
            )
            months = ", ".join(path.stem[-6:] for path in files)
            staged_outputs.append((temp_output_path, output_path, snapshot, len(files), months))

    snapshots: list[DataSnapshot] = []
    for temp_output_path, output_path, snapshot, month_count, months in staged_outputs:
        temp_output_path.replace(output_path)
        snapshots.append(snapshot)
        print(
            f"Merged yearly snapshot [{snapshot.api} {snapshot.year}] "
            f"months={month_count} ({months}), rows={snapshot.row_count}, "
            f"changed={'Y' if snapshot.is_changed else 'N'}, output={output_path}"
        )
    return snapshots


def publish_integrated_snapshots(
    api_codes: list[str],
    yearly_dir: Path,
    integrated_dir: Path,
    encoding: str,
) -> list[DataSnapshot]:
    staged_outputs: list[tuple[Path, Path, DataSnapshot, int, str]] = []
    for api_code in api_codes:
        spec = API_SPECS[api_code]
        files = yearly_files_for_api(yearly_dir, spec)
        if not files:
            continue
        output_path = integrated_output_path(integrated_dir, spec)
        temp_output_path = output_path.with_name(f"{output_path.stem}.tmp{output_path.suffix}")
        row_count = merge_files_preserving_columns(
            [path for _, path in files],
            temp_output_path,
            encoding,
        )
        checksum = file_checksum(temp_output_path)
        previous_checksum = file_checksum(output_path) if output_path.exists() else ""
        is_changed = checksum != previous_checksum
        if not previous_checksum:
            snapshot_message = "FIRST_SNAPSHOT"
        elif is_changed:
            snapshot_message = "CHANGED"
        else:
            snapshot_message = "UNCHANGED"
        snapshot = DataSnapshot(
            api=spec.display_name,
            year="ALL",
            file_path=output_path,
            row_count=row_count,
            file_size_bytes=temp_output_path.stat().st_size,
            checksum=checksum,
            previous_checksum=previous_checksum,
            is_changed=is_changed,
            message=snapshot_message,
        )
        year_text = ", ".join(str(year) for year, _ in files)
        staged_outputs.append((temp_output_path, output_path, snapshot, len(files), year_text))

    snapshots: list[DataSnapshot] = []
    for temp_output_path, output_path, snapshot, year_count, year_text in staged_outputs:
        temp_output_path.replace(output_path)
        snapshots.append(snapshot)
        print(
            f"Published integrated snapshot [{snapshot.api}] "
            f"years={year_count} ({year_text}), rows={snapshot.row_count}, "
            f"changed={'Y' if snapshot.is_changed else 'N'}, output={output_path}"
        )
    return snapshots


def yearly_files_for_api(yearly_root: Path, spec: ApiSpec) -> list[tuple[int, Path]]:
    source_dir = yearly_root / spec.output_dir_name
    if not source_dir.exists():
        return []

    files: list[tuple[int, Path]] = []
    for path in source_dir.glob("*.csv"):
        match = YEARLY_FILENAME_RE.match(path.name)
        if not match or match.group("name") != spec.display_name:
            continue
        files.append((int(match.group("year")), path))
    return sorted(files)


def integrated_output_path(integrated_root: Path, spec: ApiSpec) -> Path:
    return integrated_root / spec.output_dir_name / f"{integrated_file_stem(spec)}.csv"


def integrated_file_stem(spec: ApiSpec) -> str:
    if spec.code == "national-card":
        return "국민내일배움카드"
    if spec.code == "consortium":
        return "국가인적자원개발"
    return spec.display_name


def merge_files_preserving_columns(
    files: list[Path],
    output_path: Path,
    encoding: str,
) -> int:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    row_count = 0
    with output_path.open("w", newline="", encoding=encoding) as output_handle:
        writer = None
        columns = None
        for source_path in files:
            with source_path.open("r", newline="", encoding=encoding) as source_handle:
                reader = csv.DictReader(source_handle)
                if reader.fieldnames is None:
                    continue
                if columns is None:
                    columns = reader.fieldnames
                elif reader.fieldnames != columns:
                    raise ValueError(f"Integrated source columns changed in {source_path}")
                if writer is None:
                    writer = csv.DictWriter(output_handle, fieldnames=columns)
                    writer.writeheader()
                for row in reader:
                    writer.writerow({column: row.get(column, "") for column in columns})
                    row_count += 1
    return row_count
