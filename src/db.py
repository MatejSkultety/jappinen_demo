import sqlite3
from pathlib import Path


DB_PATH = Path("db/data_quality.db")


def ensure_db_dir() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def get_connection() -> sqlite3.Connection:
    ensure_db_dir()
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def quote_identifier(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def _normalize_sql(sql: str) -> str:
    statement = sql.strip()
    if statement.endswith(";"):
        statement = statement[:-1].strip()
    return statement


def _is_read_only_sql(sql: str) -> bool:
    if not sql:
        return False
    if ";" in sql:
        return False

    first_token = sql.lstrip().split(None, 1)[0].lower()
    return first_token in {"select", "with"}


def run_read_only_sql_query(connection: sqlite3.Connection, sql: str, max_rows: int = 100) -> dict:
    statement = _normalize_sql(sql)
    if not _is_read_only_sql(statement):
        return {
            "error": "Only single-statement read-only SELECT/WITH queries are allowed.",
        }

    allowed_actions = {
        getattr(sqlite3, "SQLITE_SELECT", None),
        getattr(sqlite3, "SQLITE_READ", None),
        getattr(sqlite3, "SQLITE_FUNCTION", None),
    }
    allowed_actions.discard(None)

    def authorizer(action_code, _param1, _param2, _db_name, _trigger_name):
        if action_code in allowed_actions:
            return sqlite3.SQLITE_OK
        return sqlite3.SQLITE_DENY

    connection.set_authorizer(authorizer)
    try:
        cursor = connection.execute(statement)
        rows = cursor.fetchmany(max_rows)
        return {
            "sql": statement,
            "columns": [description[0] for description in cursor.description or []],
            "rows": [dict(row) for row in rows],
            "returned_row_count": len(rows),
            "truncated": len(rows) == max_rows,
        }
    except sqlite3.DatabaseError as exc:
        return {"error": "SQL execution failed.", "details": str(exc)}
    finally:
        connection.set_authorizer(None)


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


def table_schema(connection: sqlite3.Connection, table_name: str) -> list[dict]:
    rows = connection.execute(f"PRAGMA table_info({quote_identifier(table_name)})").fetchall()
    return [
        {
            "name": row["name"],
            "type": row["type"],
            "notnull": bool(row["notnull"]),
            "default": row["dflt_value"],
            "primary_key": bool(row["pk"]),
        }
        for row in rows
    ]