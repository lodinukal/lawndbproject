import sqlite3
import traceback
from typing import Any

import scripts
from util import Signal


connection = sqlite3.connect("lawn_database.db")
connection.row_factory = sqlite3.Row
# connection.set_trace_callback(print)  # Enable debug output for SQL queries
cursor = connection.cursor()
database_updated = Signal()

cursor.execute("PRAGMA foreign_keys = ON")


def create_tables():
    cursor.executescript(scripts.CREATE_TABLES)
    cursor.executescript(scripts.CREATE_ADMIN_USER)
    cursor.executescript(scripts.ADD_DEFAULT_SERVICES)
    connection.commit()

    database_updated.emit()


def reset_database():
    cursor.executescript(scripts.DROP_TABLES)
    connection.commit()
    create_tables()


class QueryResult:
    error: str | None
    data: list[sqlite3.Row]
    lastrowid: int | None

    def __init__(self):
        self.error = None
        self.data = []
        self.lastrowid = None


def execute(query: str, params: dict = None) -> QueryResult:
    result = QueryResult()
    try:
        cursor.execute(query, params or {})
        connection.commit()

        # check for any results and fetch them
        rows = cursor.fetchall()
        if rows:
            result.data.extend(rows)
        if cursor.lastrowid:
            result.lastrowid = cursor.lastrowid
        if cursor.rowcount > 0:
            database_updated.emit()
    except Exception as e:
        traceback.print_exception(e)
        result.error = str(e)
        print(f"Error executing query: {result.error}")

    return result


create_tables()
