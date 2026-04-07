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