import sqlite3
from pathlib import Path
from typing import Any

from db.connection import connection


class StorageSession:
    """Small repository context for multi-step workflows sharing one connection."""

    def __init__(self, db_path: Path | str | None = None) -> None:
        self._db_path = db_path
        self._context: Any = None
        self.conn: sqlite3.Connection | None = None

    def __enter__(self) -> "StorageSession":
        self._context = connection(self._db_path)
        self.conn = self._context.__enter__()
        self.conn.execute("BEGIN")
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        assert self.conn is not None
        if exc_type is None:
            self.conn.commit()
        else:
            self.conn.rollback()
        self._context.__exit__(exc_type, exc, traceback)


def storage_session(db_path: Path | str | None = None) -> StorageSession:
    return StorageSession(db_path)
