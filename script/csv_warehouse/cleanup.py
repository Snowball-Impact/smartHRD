"""Post-run cleanup policies."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path


def cleanup_old_checkpoints(checkpoint_dir: Path, retention_days: int, now: datetime) -> int:
    if retention_days < 0 or not checkpoint_dir.exists():
        return 0

    cutoff = now - timedelta(days=retention_days)
    deleted_count = 0
    for path in checkpoint_dir.glob("*.json"):
        if not path.is_file():
            continue
        modified_at = datetime.fromtimestamp(path.stat().st_mtime)
        if modified_at >= cutoff:
            continue
        path.unlink()
        deleted_count += 1
    return deleted_count

