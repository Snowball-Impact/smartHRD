"""Default paths for the SmartHRD CSV Warehouse pipeline."""

from __future__ import annotations

from pathlib import Path


DEFAULT_WAREHOUSE_DIR = Path("warehouse")
DEFAULT_MONTHLY_DIR = Path("dataset/work24/monthly")
DEFAULT_YEARLY_DIR = Path("dataset/work24/yearly")
DEFAULT_CHECKPOINT_DIR = DEFAULT_WAREHOUSE_DIR / "checkpoints"
DEFAULT_ENV_FILE = Path(".env")


def warehouse_log_path(warehouse_dir: Path, file_name: str) -> Path:
    return warehouse_dir / "logs" / file_name

