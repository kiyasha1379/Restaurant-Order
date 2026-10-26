"""Database connection settings applied to every SQLite connection."""

import sqlite3

from sqlalchemy import event
from sqlalchemy.engine import Engine


@event.listens_for(Engine, "connect")
def _configure_sqlite_connection(dbapi_connection: object, _connection_record: object) -> None:
    """Turn on foreign keys and WAL mode for each new SQLite connection.

    Foreign keys are off by default in SQLite; WAL lets readers and a writer
    work at the same time. Other database types are left untouched.
    """
    if not isinstance(dbapi_connection, sqlite3.Connection):
        return
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.close()
