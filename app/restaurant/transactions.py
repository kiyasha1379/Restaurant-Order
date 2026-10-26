"""Transaction helpers that depend on the database engine."""

import sqlite3

from sqlalchemy.orm import Session


def begin_immediate(session: Session) -> None:
    """Take SQLite's write lock now, before reading what the next write depends on.

    A check followed by an insert is only safe when nobody else can write in between:
    `BEGIN IMMEDIATE` makes a second writer wait (up to the busy timeout) until this
    transaction commits, so two requests for the same table and time are decided one after
    the other. When the session already wrote something it holds the lock, and other
    database engines are left alone (they lock rows in their own way).
    """
    connection = session.connection()
    raw_connection = connection.connection.dbapi_connection
    if not isinstance(raw_connection, sqlite3.Connection) or raw_connection.in_transaction:
        return
    connection.exec_driver_sql("BEGIN IMMEDIATE")
