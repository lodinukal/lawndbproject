import sqlite3
import traceback

import scripts
from util import Signal


connection = sqlite3.connect("lawn_database.db")
connection.row_factory = sqlite3.Row
cursor = connection.cursor()
database_updated = Signal()

cursor.execute("PRAGMA foreign_keys = ON")


def create_tables():
    cursor.executescript(scripts.CREATE_TABLES)
    cursor.executescript(scripts.CREATE_ADMIN_USER)
    connection.commit()

    database_updated.emit()


def reset_database():
    cursor.executescript(scripts.DROP_TABLES)
    connection.commit()
    create_tables()


class QueryResult:
    error: str | None
    data: list[sqlite3.Row]

    def __init__(self):
        self.error = None
        self.data = []


def execute(query: str, params: dict = None) -> QueryResult:
    result = QueryResult()
    try:
        cursor.execute(query, params or {})
        connection.commit()

        # check for any results and fetch them
        rows = cursor.fetchall()
        if rows:
            result.data.extend(rows)
        if cursor.rowcount > 0:
            database_updated.emit()
    except Exception as e:
        result.error = str(e)
        print(f"Error executing query: {result.error}")
        traceback.print_stack()

    return result


create_tables()
