from __future__ import annotations

from typing import Any

from .db import list_tables, run_read_only_sql_query, table_columns, table_row_count, table_schema
from .profiling import column_numeric_stats, distinct_count, missing_values_by_column, profile_table


TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "list_tables",
        "description": "List all SQLite tables currently available.",
        "parameters": {"type": "object", "properties": {}, "required": []},
        "executor": lambda connection, _: list_tables(connection),
    },
    {
        "name": "table_row_count",
        "description": "Return the number of rows in a table.",
        "parameters": {
            "type": "object",
            "properties": {"table_name": {"type": "string"}},
            "required": ["table_name"],
        },
        "executor": lambda connection, arguments: table_row_count(connection, arguments["table_name"]),
    },
    {
        "name": "table_columns",
        "description": "Return the column names for a table.",
        "parameters": {
            "type": "object",
            "properties": {"table_name": {"type": "string"}},
            "required": ["table_name"],
        },
        "executor": lambda connection, arguments: table_columns(connection, arguments["table_name"]),
    },
    {
        "name": "table_schema",
        "description": "Return schema details for all columns in a table.",
        "parameters": {
            "type": "object",
            "properties": {"table_name": {"type": "string"}},
            "required": ["table_name"],
        },
        "executor": lambda connection, arguments: table_schema(connection, arguments["table_name"]),
    },
    {
        "name": "missing_values_by_column",
        "description": "Return missing-value counts for each column in a table.",
        "parameters": {
            "type": "object",
            "properties": {"table_name": {"type": "string"}},
            "required": ["table_name"],
        },
        "executor": lambda connection, arguments: missing_values_by_column(connection, arguments["table_name"]),
    },
    {
        "name": "profile_table",
        "description": "Return a small profile summary for a table.",
        "parameters": {
            "type": "object",
            "properties": {"table_name": {"type": "string"}},
            "required": ["table_name"],
        },
        "executor": lambda connection, arguments: profile_table(connection, arguments["table_name"]),
    },
    {
        "name": "distinct_count",
        "description": "Return the number of distinct values in a column.",
        "parameters": {
            "type": "object",
            "properties": {
                "table_name": {"type": "string"},
                "column_name": {"type": "string"},
            },
            "required": ["table_name", "column_name"],
        },
        "executor": lambda connection, arguments: distinct_count(
            connection, arguments["table_name"], arguments["column_name"]
        ),
    },
    {
        "name": "column_numeric_stats",
        "description": "Return basic numeric statistics for a column.",
        "parameters": {
            "type": "object",
            "properties": {
                "table_name": {"type": "string"},
                "column_name": {"type": "string"},
            },
            "required": ["table_name", "column_name"],
        },
        "executor": lambda connection, arguments: column_numeric_stats(
            connection, arguments["table_name"], arguments["column_name"]
        ),
    },
    {
        "name": "read_only_sql_query",
        "description": "Execute a single read-only SELECT or WITH SQL query and return rows.",
        "parameters": {
            "type": "object",
            "properties": {
                "sql": {"type": "string"},
            },
            "required": ["sql"],
        },
        "executor": lambda connection, arguments: run_read_only_sql_query(connection, arguments["sql"]),
    },
]


def get_tool_registry() -> dict[str, dict[str, Any]]:
    return {
        tool_definition["name"]: {
            "description": tool_definition["description"],
            "executor": tool_definition["executor"],
        }
        for tool_definition in TOOL_DEFINITIONS
    }


def get_tool_schemas() -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": tool_definition["name"],
                "description": tool_definition["description"],
                "parameters": tool_definition["parameters"],
            },
        }
        for tool_definition in TOOL_DEFINITIONS
    ]