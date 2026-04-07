from .db import get_connection, quote_identifier, table_columns, table_row_count


def missing_values_by_column(connection, table_name: str) -> dict[str, int]:
    columns = table_columns(connection, table_name)
    if not columns:
        return {}

    expressions = [
        f"SUM(CASE WHEN {quote_identifier(column)} IS NULL OR TRIM(CAST({quote_identifier(column)} AS TEXT)) = '' THEN 1 ELSE 0 END) AS {quote_identifier(column)}"
        for column in columns
    ]
    row = connection.execute(f"SELECT {', '.join(expressions)} FROM {quote_identifier(table_name)}").fetchone()
    return {column: int(row[column] or 0) for column in columns}


def distinct_count(connection, table_name: str, column_name: str) -> int:
    row = connection.execute(
        f"SELECT COUNT(DISTINCT {quote_identifier(column_name)}) AS count FROM {quote_identifier(table_name)}"
    ).fetchone()
    return int(row["count"])


def column_numeric_stats(connection, table_name: str, column_name: str) -> dict:
    rows = connection.execute(
        f"SELECT {quote_identifier(column_name)} AS value FROM {quote_identifier(table_name)} WHERE {quote_identifier(column_name)} IS NOT NULL"
    ).fetchall()

    numeric_values: list[float] = []
    non_numeric_count = 0

    for row in rows:
        value = row["value"]
        if isinstance(value, bool):
            numeric_values.append(float(value))
            continue
        if isinstance(value, (int, float)):
            numeric_values.append(float(value))
            continue
        if isinstance(value, str):
            try:
                numeric_values.append(float(value.strip()))
                continue
            except ValueError:
                non_numeric_count += 1
                continue
        non_numeric_count += 1

    return {
        "table": table_name,
        "column": column_name,
        "non_null_count": len(rows),
        "numeric_count": len(numeric_values),
        "non_numeric_count": non_numeric_count,
        "min": min(numeric_values) if numeric_values else None,
        "max": max(numeric_values) if numeric_values else None,
        "avg": (sum(numeric_values) / len(numeric_values)) if numeric_values else None,
    }


def profile_table(connection, table_name: str) -> dict:
    columns = table_columns(connection, table_name)
    missing_values = missing_values_by_column(connection, table_name)
    return {
        "table": table_name,
        "rows": table_row_count(connection, table_name),
        "columns": columns,
        "missing_total": sum(missing_values.values()),
        "missing_by_column": missing_values,
    }


def table_summaries(table_names: list[str]) -> list[dict]:
    with get_connection() as connection:
        return [profile_table(connection, table_name) for table_name in table_names]