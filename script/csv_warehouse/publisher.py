"""Publish monthly Work24 CSV files into yearly snapshots."""

from __future__ import annotations

from pathlib import Path

from csv_warehouse.snapshot import DataSnapshot, file_checksum
from work24_collector.config import API_SPECS
from yearly_csv_merge import merge_monthly_files, monthly_files_for_year, validate_monthly_files, yearly_output_path


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

