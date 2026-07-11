from __future__ import annotations

import argparse
from datetime import datetime, timedelta


def parse_yyyymmdd(value: str) -> datetime:
    try:
        return datetime.strptime(value, "%Y%m%d")
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"Invalid date '{value}'. Use YYYYMMDD.") from exc


def month_ranges(start: datetime, end: datetime) -> list[tuple[str, str]]:
    if start > end:
        raise argparse.ArgumentTypeError("--start must be earlier than or equal to --end.")

    ranges: list[tuple[str, str]] = []
    cursor = datetime(start.year, start.month, 1)
    while cursor <= end:
        next_month = datetime(cursor.year + (cursor.month // 12), (cursor.month % 12) + 1, 1)
        month_start = max(start, cursor)
        month_end = min(end, next_month - timedelta(days=1))
        ranges.append((month_start.strftime("%Y%m%d"), month_end.strftime("%Y%m%d")))
        cursor = next_month
    return ranges

