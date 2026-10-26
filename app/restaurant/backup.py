"""Database backups: a consistent copy of the SQLite file, with old copies pruned."""

import sqlite3
from datetime import datetime
from pathlib import Path

BACKUP_PREFIX = "restaurant-"
BACKUP_SUFFIX = ".db"
TIMESTAMP_FORMAT = "%Y%m%d-%H%M%S"


def backup_database(source: Path, target_folder: Path, now: datetime, keep: int) -> Path:
    """Copy the live database into `target_folder` and keep only the newest `keep` copies.

    SQLite's own backup call is used, so the copy is consistent even while the site writes
    (copying the file by hand could catch it half-written). Returns the new copy's path.
    """
    if not source.is_file():
        raise FileNotFoundError(f"No database file at {source}")
    target_folder.mkdir(parents=True, exist_ok=True)
    target = target_folder / f"{BACKUP_PREFIX}{now.strftime(TIMESTAMP_FORMAT)}{BACKUP_SUFFIX}"
    with sqlite3.connect(source) as live, sqlite3.connect(target) as copy:
        live.backup(copy)
    copy.close()
    live.close()
    prune_backups(target_folder, keep)
    return target


def prune_backups(folder: Path, keep: int) -> list[Path]:
    """Delete all but the newest `keep` backups (their names sort by time); return the deleted."""
    copies = sorted(folder.glob(f"{BACKUP_PREFIX}*{BACKUP_SUFFIX}"))
    doomed = copies[: max(len(copies) - max(keep, 1), 0)]
    for path in doomed:
        path.unlink()
    return doomed
