"""Merge monthly Work24 API CSV files into yearly CSV files."""

from __future__ import annotations

import argparse
import calendar
import csv
import json
import re
import sys
from pathlib import Path

from work24_collector.config import (
    API_COLLECTION_ORDER,
    API_SPECS,
    NON_NATIONAL_CARD_COLLECTION_ORDER,
    ApiSpec,
)


MONTHLY_FILENAME_RE = re.compile(r"^(?P<name>.+)_(?P<year>\d{4})(?P<month>0[1-9]|1[0-2])\.csv$")


def parse_args(argv: list[str]) -> argparse.Namespace:
    class HelpFormatter(argparse.ArgumentDefaultsHelpFormatter, argparse.RawDescriptionHelpFormatter):
        pass

    parser = argparse.ArgumentParser(
        description="Merge monthly Work24 API CSV files into yearly CSV files.",
        formatter_class=HelpFormatter,
        epilog="""Examples:
  python script\\yearly_csv_merge.py --api national-card --year 2024
  python script\\yearly_csv_merge.py --api non-national-card --year 2024
  python script\\yearly_csv_merge.py --api all
""",
    )
    parser.add_argument(
        "--api",
        choices=["all", "non-national-card", *API_COLLECTION_ORDER],
        required=True,
        help="API to merge. Use 'all' for every API, or 'non-national-card' for the three smaller APIs.",
    )
    parser.add_argument(
        "--year",
        type=int,
        action="append",
        help="Year to merge. Can be used multiple times. If omitted, all detected years are merged.",
    )
    parser.add_argument(
        "--monthly-dir",
        type=Path,
        default=Path("dataset/work24/monthly"),
        help="Monthly CSV root directory.",
    )
    parser.add_argument(
        "--yearly-dir",
        type=Path,
        default=Path("dataset/work24/yearly"),
        help="Yearly CSV root directory.",
    )
    parser.add_argument(
        "--checkpoint-dir",
        type=Path,
        default=Path("warehouse/checkpoints"),
        help="Checkpoint directory.",
    )
    parser.add_argument("--encoding", default="utf-8-sig", help="CSV encoding.")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite an existing yearly CSV file.")
    parser.add_argument(
        "--allow-incomplete",
        action="store_true",
        help="Allow merge even when checkpoint or CSV row validation detects incomplete monthly files.",
    )
    return parser.parse_args(argv)


def selected_api_codes(api: str) -> list[str]:
    if api == "all":
        return list(API_COLLECTION_ORDER)
    if api == "non-national-card":
        return list(NON_NATIONAL_CARD_COLLECTION_ORDER)
    return [api]


def monthly_files_for_year(monthly_root: Path, spec: ApiSpec, year: int) -> list[Path]:
    source_dir = monthly_root / spec.output_dir_name
    if not source_dir.exists():
        return []

    matched: list[tuple[int, Path]] = []
    for path in source_dir.glob("*.csv"):
        match = MONTHLY_FILENAME_RE.match(path.name)
        if not match:
            continue
        if match.group("name") != spec.display_name:
            continue
        if int(match.group("year")) != year:
            continue
        matched.append((int(match.group("month")), path))

    return [path for _, path in sorted(matched)]


def detected_years(monthly_root: Path, spec: ApiSpec) -> list[int]:
    source_dir = monthly_root / spec.output_dir_name
    if not source_dir.exists():
        return []

    years = set()
    for path in source_dir.glob("*.csv"):
        match = MONTHLY_FILENAME_RE.match(path.name)
        if match and match.group("name") == spec.display_name:
            years.add(int(match.group("year")))
    return sorted(years)


def yearly_output_path(yearly_root: Path, spec: ApiSpec, year: int) -> Path:
    return yearly_root / spec.output_dir_name / f"{spec.display_name}_{year}.csv"


def file_month(path: Path) -> tuple[int, int]:
    match = MONTHLY_FILENAME_RE.match(path.name)
    if not match:
        raise ValueError(f"Not a monthly file name: {path}")
    return int(match.group("year")), int(match.group("month"))


def data_row_count(path: Path, encoding: str) -> int:
    with path.open("r", newline="", encoding=encoding) as handle:
        return max(sum(1 for _ in handle) - 1, 0)


def checkpoint_path(checkpoint_dir: Path, spec: ApiSpec, year: int, month: int) -> Path:
    last_day = calendar.monthrange(year, month)[1]
    return checkpoint_dir / f"{spec.code}_{year}{month:02d}01_{year}{month:02d}{last_day:02d}.json"


def validate_monthly_files(
    files: list[Path],
    spec: ApiSpec,
    checkpoint_dir: Path,
    encoding: str,
    allow_incomplete: bool,
) -> None:
    errors: list[str] = []
    warnings: list[str] = []

    for path in files:
        year, month = file_month(path)
        checkpoint = checkpoint_path(checkpoint_dir, spec, year, month)
        rows = data_row_count(path, encoding)

        if not checkpoint.exists():
            warnings.append(f"No checkpoint for {path}; rows={rows}")
            continue

        data = json.loads(checkpoint.read_text(encoding="utf-8"))
        expected_count = data.get("expected_count")
        collected_count = data.get("collected_count")
        completed = bool(data.get("completed"))

        if expected_count is None:
            warnings.append(f"No expected_count in checkpoint {checkpoint}; rows={rows}")
            continue

        if completed and rows == collected_count:
            if expected_count != collected_count:
                warnings.append(
                    f"Count hint mismatch for completed monthly file: {path} "
                    f"rows={rows}, collected={collected_count}, expected_hint={expected_count}"
                )
            continue

        if rows != expected_count or collected_count != expected_count:
            errors.append(
                f"Incomplete monthly file: {path} "
                f"rows={rows}, checkpoint_collected={collected_count}, expected={expected_count}"
            )

    for warning in warnings:
        print(f"Warning: {warning}")

    if errors and not allow_incomplete:
        error_text = "\n".join(errors)
        raise ValueError(f"Monthly validation failed. Recollect incomplete files or use --allow-incomplete.\n{error_text}")

    for error in errors:
        print(f"Warning: {error}")


def merge_monthly_files(files: list[Path], output_path: Path, encoding: str, overwrite: bool) -> int:
    if not files:
        return 0
    if output_path.exists() and not overwrite:
        raise FileExistsError(f"{output_path} already exists. Use --overwrite to replace it.")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    expected_header: list[str] | None = None
    row_count = 0
    with output_path.open("w", newline="", encoding=encoding) as output_handle:
        writer: csv.writer | None = None
        for source_path in files:
            with source_path.open("r", newline="", encoding=encoding) as source_handle:
                reader = csv.reader(source_handle)
                try:
                    header = next(reader)
                except StopIteration:
                    print(f"Skip empty file: {source_path}")
                    continue

                if expected_header is None:
                    expected_header = header
                    writer = csv.writer(output_handle)
                    writer.writerow(header)
                elif header != expected_header:
                    raise ValueError(f"Column mismatch: {source_path}")

                assert writer is not None
                for row in reader:
                    writer.writerow(row)
                    row_count += 1

    return row_count


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    try:
        for api_code in selected_api_codes(args.api):
            spec = API_SPECS[api_code]
            years = sorted(set(args.year or detected_years(args.monthly_dir, spec)))
            if not years:
                print(f"No monthly files found for {spec.display_name}.")
                continue

            for year in years:
                files = monthly_files_for_year(args.monthly_dir, spec, year)
                output_path = yearly_output_path(args.yearly_dir, spec, year)
                if not files:
                    print(f"No monthly files found [{spec.display_name} {year}].")
                    continue

                validate_monthly_files(files, spec, args.checkpoint_dir, args.encoding, args.allow_incomplete)
                row_count = merge_monthly_files(files, output_path, args.encoding, args.overwrite)
                months = ", ".join(path.stem[-6:] for path in files)
                print(
                    f"Merged [{spec.display_name} {year}] months={len(files)} ({months}), "
                    f"rows={row_count}, output={output_path}"
                )
    except (FileExistsError, ValueError) as exc:
        print(exc, file=sys.stderr)
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
