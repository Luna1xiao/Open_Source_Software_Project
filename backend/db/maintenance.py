import shutil
import sqlite3
from pathlib import Path

from db.connection import connect, resolve_db_path


def backup_database(target_path: Path | str, db_path: Path | str | None = None) -> Path:
    """Copy the current SQLite database into target_path using SQLite backup."""
    resolved_target = Path(target_path)
    resolved_target.parent.mkdir(parents=True, exist_ok=True)
    source = connect(db_path)
    try:
        destination = sqlite3.connect(resolved_target)
        try:
            source.backup(destination)
        finally:
            destination.close()
    finally:
        source.close()
    return resolved_target


def copy_database_file(target_path: Path | str, db_path: Path | str | None = None) -> Path:
    """Copy the database file directly; use backup_database while the app is running."""
    resolved_source = resolve_db_path(db_path)
    if not isinstance(resolved_source, Path):
        raise ValueError("copy_database_file requires a file-backed database")
    resolved_target = Path(target_path)
    resolved_target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(resolved_source, resolved_target)
    return resolved_target
