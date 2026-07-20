"""Yearly CSV file snapshot helpers."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DataSnapshot:
    api: str
    year: int
    file_path: Path
    row_count: int
    file_size_bytes: int
    checksum: str
    previous_checksum: str
    is_changed: bool
    message: str


def file_checksum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

