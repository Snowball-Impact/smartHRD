"""Compare old yearly CSV snapshots with newly merged yearly CSV snapshots."""

from __future__ import annotations

import argparse
import csv
import hashlib
import sys
from dataclasses import dataclass
from pathlib import Path

from work24_collector.config import API_COLLECTION_ORDER, API_SPECS, NON_NATIONAL_CARD_COLLECTION_ORDER, ApiSpec


DEFAULT_KEY_COLUMNS = ["trprId", "trprDegr", "trainstCstId", "traStartDate", "traEndDate"]

OLD_YEARLY_PATHS = {
    ("national-card", 2023): Path("dataset/backup/국민내일배움카드/고용24API_국민내일배움카드훈련과정_2023년.csv"),
    ("national-card", 2024): Path("dataset/backup/국민내일배움카드/고용24API_국민내일배움카드훈련과정_2024년.csv"),
    ("employer", 2023): Path("dataset/backup/사업주훈련/사업주훈련_2023년도_총396546개.csv"),
    ("employer", 2024): Path("dataset/backup/사업주훈련/사업주훈련_2024년도_총337566개.csv"),
    ("consortium", 2023): Path("dataset/backup/국가인적자원개발컨소시엄/국가인적자원개발 컨소시엄_2023년도_총15778개.csv"),
    ("consortium", 2024): Path("dataset/backup/국가인적자원개발컨소시엄/국가인적자원개발 컨소시엄_2024년도_총17506개.csv"),
    ("work-study", 2023): Path("dataset/backup/일학습병행/일학습병행_2023년도_총6478개.csv"),
    ("work-study", 2024): Path("dataset/backup/일학습병행/일학습병행_2024년도_총6692개.csv"),
}


@dataclass
class RowRecord:
    row: dict[str, str]
    row_hash: str


@dataclass
class CsvSnapshot:
    path: Path
    header: list[str]
    records: dict[tuple[str, ...], RowRecord]
    duplicate_count: int


def parse_args(argv: list[str]) -> argparse.Namespace:
    class HelpFormatter(argparse.ArgumentDefaultsHelpFormatter, argparse.RawDescriptionHelpFormatter):
        pass

    parser = argparse.ArgumentParser(
        description="Compare old backup yearly CSVs with newly merged yearly CSVs.",
        formatter_class=HelpFormatter,
        epilog="""Examples:
  python script\\compare_yearly_changes.py --api all --year 2024 --summary-only
  python script\\compare_yearly_changes.py --api non-national-card --year 2024 --write-details
""",
    )
    parser.add_argument(
        "--api",
        choices=["all", "non-national-card", *API_COLLECTION_ORDER],
        required=True,
        help="API to compare.",
    )
    parser.add_argument(
        "--year",
        type=int,
        action="append",
        help="Year to compare. Can be used multiple times. If omitted, comparable years are used.",
    )
    parser.add_argument(
        "--new-yearly-dir",
        type=Path,
        default=Path("dataset/work24/yearly"),
        help="New yearly CSV root.",
    )
    parser.add_argument("--output-dir", type=Path, default=Path("analysis/changes"), help="Diff output directory.")
    parser.add_argument("--encoding", default="utf-8-sig", help="CSV encoding.")
    parser.add_argument(
        "--key-columns",
        nargs="+",
        default=DEFAULT_KEY_COLUMNS,
        help="Columns used as a row identity key.",
    )
    parser.add_argument("--write-details", action="store_true", help="Write added, removed, and changed detail CSVs.")
    return parser.parse_args(argv)


def selected_api_codes(api: str) -> list[str]:
    if api == "all":
        return list(API_COLLECTION_ORDER)
    if api == "non-national-card":
        return list(NON_NATIONAL_CARD_COLLECTION_ORDER)
    return [api]


def comparable_years(api_code: str, requested_years: list[int] | None) -> list[int]:
    if requested_years:
        return sorted(set(requested_years))
    return sorted(year for code, year in OLD_YEARLY_PATHS if code == api_code)


def new_yearly_path(new_yearly_root: Path, spec: ApiSpec, year: int) -> Path:
    return new_yearly_root / spec.output_dir_name / f"{spec.display_name}_{year}.csv"


def normalized(value: str | None) -> str:
    return "" if value is None else value.strip()


def row_key(row: dict[str, str], key_columns: list[str]) -> tuple[str, ...]:
    return tuple(normalized(row.get(column)) for column in key_columns)


def comparable_hash(row: dict[str, str], columns: list[str]) -> str:
    payload = "\x1f".join(normalized(row.get(column)) for column in columns)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def load_snapshot(path: Path, key_columns: list[str], compare_columns: list[str], encoding: str) -> CsvSnapshot:
    records: dict[tuple[str, ...], RowRecord] = {}
    duplicate_count = 0

    with path.open("r", newline="", encoding=encoding) as handle:
        reader = csv.DictReader(handle)
        header = list(reader.fieldnames or [])
        missing_keys = [column for column in key_columns if column not in header]
        if missing_keys:
            raise ValueError(f"Missing key columns in {path}: {missing_keys}")

        for row in reader:
            key = row_key(row, key_columns)
            if key in records:
                duplicate_count += 1
                continue
            records[key] = RowRecord(row=row, row_hash=comparable_hash(row, compare_columns))

    return CsvSnapshot(path=path, header=header, records=records, duplicate_count=duplicate_count)


def read_header(path: Path, encoding: str) -> list[str]:
    with path.open("r", newline="", encoding=encoding) as handle:
        reader = csv.reader(handle)
        return next(reader, [])


def write_rows(path: Path, rows: list[dict[str, str]], fieldnames: list[str], encoding: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding=encoding) as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_changed_cells(
    path: Path,
    old_snapshot: CsvSnapshot,
    new_snapshot: CsvSnapshot,
    changed_keys: list[tuple[str, ...]],
    key_columns: list[str],
    compare_columns: list[str],
    encoding: str,
) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    fieldnames = [*key_columns, "column", "old_value", "new_value"]

    with path.open("w", newline="", encoding=encoding) as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for key in changed_keys:
            old_row = old_snapshot.records[key].row
            new_row = new_snapshot.records[key].row
            key_values = dict(zip(key_columns, key, strict=True))
            for column in compare_columns:
                old_value = normalized(old_row.get(column))
                new_value = normalized(new_row.get(column))
                if old_value == new_value:
                    continue
                writer.writerow({**key_values, "column": column, "old_value": old_value, "new_value": new_value})
                count += 1

    return count


def compare_pair(
    api_code: str,
    year: int,
    old_path: Path,
    new_path: Path,
    key_columns: list[str],
    output_dir: Path,
    encoding: str,
    write_details: bool,
) -> dict[str, str | int]:
    old_header = read_header(old_path, encoding)
    new_header = read_header(new_path, encoding)
    compare_columns = [column for column in new_header if column in old_header]
    old_only_columns = [column for column in old_header if column not in new_header]
    new_only_columns = [column for column in new_header if column not in old_header]

    old_snapshot = load_snapshot(old_path, key_columns, compare_columns, encoding)
    new_snapshot = load_snapshot(new_path, key_columns, compare_columns, encoding)

    old_keys = set(old_snapshot.records)
    new_keys = set(new_snapshot.records)
    added_keys = sorted(new_keys - old_keys)
    removed_keys = sorted(old_keys - new_keys)
    shared_keys = old_keys & new_keys
    changed_keys = sorted(
        key for key in shared_keys if old_snapshot.records[key].row_hash != new_snapshot.records[key].row_hash
    )
    unchanged_count = len(shared_keys) - len(changed_keys)

    changed_cell_count = ""
    if write_details:
        pair_dir = output_dir / f"{api_code}_{year}"
        key_prefixes = [f"key_{column}" for column in key_columns]

        added_rows = [
            {**dict(zip(key_prefixes, key, strict=True)), **new_snapshot.records[key].row} for key in added_keys
        ]
        removed_rows = [
            {**dict(zip(key_prefixes, key, strict=True)), **old_snapshot.records[key].row} for key in removed_keys
        ]
        changed_new_rows = [
            {**dict(zip(key_prefixes, key, strict=True)), **new_snapshot.records[key].row} for key in changed_keys
        ]

        write_rows(pair_dir / "added_rows.csv", added_rows, [*key_prefixes, *new_header], encoding)
        write_rows(pair_dir / "removed_rows.csv", removed_rows, [*key_prefixes, *old_header], encoding)
        write_rows(pair_dir / "changed_rows_new.csv", changed_new_rows, [*key_prefixes, *new_header], encoding)
        changed_cell_count = write_changed_cells(
            pair_dir / "changed_cells.csv",
            old_snapshot,
            new_snapshot,
            changed_keys,
            key_columns,
            compare_columns,
            encoding,
        )

    return {
        "api": api_code,
        "year": year,
        "old_file": str(old_path),
        "new_file": str(new_path),
        "old_rows": len(old_snapshot.records),
        "new_rows": len(new_snapshot.records),
        "old_duplicate_keys": old_snapshot.duplicate_count,
        "new_duplicate_keys": new_snapshot.duplicate_count,
        "shared_rows": len(shared_keys),
        "added_rows": len(added_keys),
        "removed_rows": len(removed_keys),
        "changed_rows": len(changed_keys),
        "unchanged_rows": unchanged_count,
        "changed_cells": changed_cell_count,
        "compare_columns": len(compare_columns),
        "old_only_columns": "|".join(old_only_columns),
        "new_only_columns": "|".join(new_only_columns),
    }


def write_summary(path: Path, rows: list[dict[str, str | int]], encoding: str) -> None:
    fieldnames = [
        "api",
        "year",
        "old_rows",
        "new_rows",
        "shared_rows",
        "added_rows",
        "removed_rows",
        "changed_rows",
        "unchanged_rows",
        "changed_cells",
        "old_duplicate_keys",
        "new_duplicate_keys",
        "compare_columns",
        "old_only_columns",
        "new_only_columns",
        "old_file",
        "new_file",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding=encoding) as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    summaries: list[dict[str, str | int]] = []

    for api_code in selected_api_codes(args.api):
        spec = API_SPECS[api_code]
        for year in comparable_years(api_code, args.year):
            old_path = OLD_YEARLY_PATHS.get((api_code, year))
            new_path = new_yearly_path(args.new_yearly_dir, spec, year)
            if old_path is None or not old_path.exists():
                print(f"Skip missing old snapshot [{api_code} {year}]: {old_path}")
                continue
            if not new_path.exists():
                print(f"Skip missing new snapshot [{api_code} {year}]: {new_path}")
                continue

            summary = compare_pair(
                api_code=api_code,
                year=year,
                old_path=old_path,
                new_path=new_path,
                key_columns=args.key_columns,
                output_dir=args.output_dir,
                encoding=args.encoding,
                write_details=args.write_details,
            )
            summaries.append(summary)
            print(
                f"Compared [{api_code} {year}] old={summary['old_rows']}, new={summary['new_rows']}, "
                f"added={summary['added_rows']}, removed={summary['removed_rows']}, "
                f"changed={summary['changed_rows']}"
            )

    write_summary(args.output_dir / "summary.csv", summaries, args.encoding)
    print(f"Summary written: {args.output_dir / 'summary.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
