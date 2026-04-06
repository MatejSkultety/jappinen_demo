import sqlite3

from .config import DB_PATH


def ensure_db_dir() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def get_connection() -> sqlite3.Connection:
    ensure_db_dir()
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def quote_identifier(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def list_tables(connection: sqlite3.Connection) -> list[str]:
    rows = connection.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    ).fetchall()
    return [row["name"] for row in rows]


def drop_table(connection: sqlite3.Connection, table_name: str) -> None:
    connection.execute(f"DROP TABLE IF EXISTS {quote_identifier(table_name)}")


def table_row_count(connection: sqlite3.Connection, table_name: str) -> int:
    row = connection.execute(f"SELECT COUNT(*) AS count FROM {quote_identifier(table_name)}").fetchone()
    return int(row["count"])


def table_columns(connection: sqlite3.Connection, table_name: str) -> list[str]:
    rows = connection.execute(f"PRAGMA table_info({quote_identifier(table_name)})").fetchall()
    return [row["name"] for row in rows]