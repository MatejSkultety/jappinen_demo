from pathlib import Path
import re

import pandas as pd

from .db import drop_table, get_connection, list_tables


def normalize_name(value: str) -> str:
    value = re.sub(r"[^0-9a-zA-Z]+", "_", value.lower()).strip("_")
    if not value:
        return "table"
    if value[0].isdigit():
        return f"t_{value}"
    return value


def table_name_for_sheet(file_name: str, sheet_name: str) -> str:
    return f"{normalize_name(Path(file_name).stem)}__{normalize_name(sheet_name)}"


def dataset_name_from_table(table_name: str) -> str:
    return table_name.split("__", 1)[0]


def list_datasets() -> list[str]:
    with get_connection() as connection:
        dataset_names = {dataset_name_from_table(table_name) for table_name in list_tables(connection)}
    return sorted(dataset_names)


def tables_for_dataset(dataset_name: str) -> list[str]:
    prefix = f"{normalize_name(dataset_name)}__"
    with get_connection() as connection:
        return [table_name for table_name in list_tables(connection) if table_name.startswith(prefix)]


def tables_for_datasets(dataset_names: list[str]) -> list[str]:
    tables: list[str] = []
    for dataset_name in dataset_names:
        tables.extend(tables_for_dataset(dataset_name))
    return sorted(set(tables))


def delete_dataset(dataset_name: str) -> None:
    prefix = f"{normalize_name(dataset_name)}__"
    with get_connection() as connection:
        for table_name in list_tables(connection):
            if table_name.startswith(prefix):
                drop_table(connection, table_name)


def ingest_excel_file(uploaded_file) -> str:
    source_name = Path(uploaded_file.name).stem
    frames = pd.read_excel(uploaded_file, sheet_name=None)
    prefix = f"{normalize_name(source_name)}__"

    with get_connection() as connection:
        for table_name in list_tables(connection):
            if table_name.startswith(prefix):
                drop_table(connection, table_name)

        for sheet_name, frame in frames.items():
            table_name = table_name_for_sheet(uploaded_file.name, sheet_name)
            frame.to_sql(table_name, connection, if_exists="replace", index=False)

    return normalize_name(source_name)