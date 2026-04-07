import json

import streamlit as st
from openai import OpenAI

from src.config import OPENAI_API_KEY
from src.db import get_connection, table_columns, table_row_count
from src.ingest import list_datasets, tables_for_datasets
from src.profiling import missing_values_by_column, profile_table


def match_table_name(question: str, tables: list[str]) -> str | None:
    question_lower = question.lower()
    for table_name in tables:
        if table_name.lower() in question_lower:
            return table_name
    for table_name in tables:
        short_name = table_name.split("__", 1)[-1].replace("_", " ")
        if short_name in question_lower:
            return table_name
    return tables[0] if len(tables) == 1 else None


def classify_question(question: str, tables: list[str]) -> dict:
    question_lower = question.lower()
    if any(text in question_lower for text in ["what tables", "available tables", "list tables"]):
        return {"intent": "list_tables"}
    if any(text in question_lower for text in ["how many rows", "row count", "number of rows"]):
        return {"intent": "row_count", "table": match_table_name(question, tables)}
    if "column" in question_lower and "missing" not in question_lower:
        return {"intent": "columns", "table": match_table_name(question, tables)}
    if "missing" in question_lower:
        return {"intent": "missing_values", "table": match_table_name(question, tables)}
    if any(text in question_lower for text in ["profile", "summary", "overview"]):
        return {"intent": "profile_table", "table": match_table_name(question, tables)}

    if not OPENAI_API_KEY:
        return {"intent": "unsupported"}

    client = OpenAI(api_key=OPENAI_API_KEY)
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0,
        messages=[
            {
                "role": "system",
                "content": (
                    "Classify the user's question for a simple data-quality assistant. "
                    "Return JSON with keys intent, table, column. "
                    "Allowed intent values: list_tables, row_count, columns, missing_values, profile_table, unsupported."
                ),
            },
            {"role": "user", "content": f"Tables: {tables}\nQuestion: {question}"},
        ],
    )

    try:
        return json.loads(response.choices[0].message.content or "{}")
    except json.JSONDecodeError:
        return {"intent": "unsupported"}


def answer_question(question: str, tables: list[str]) -> str:
    if not tables:
        return "No tables were created for the selected datasets yet."

    intent = classify_question(question, tables)
    intent_name = intent.get("intent")
    table_name = intent.get("table") or match_table_name(question, tables)

    with get_connection() as connection:
        if intent_name == "list_tables":
            return "Available tables: " + ", ".join(tables)

        if intent_name == "row_count" and table_name:
            return f"{table_name}: {table_row_count(connection, table_name)} rows."

        if intent_name == "columns" and table_name:
            columns = table_columns(connection, table_name)
            return f"{table_name} columns: {', '.join(columns) if columns else 'no columns found'}."

        if intent_name == "missing_values" and table_name:
            missing = missing_values_by_column(connection, table_name)
            total_missing = sum(missing.values())
            details = [f"{column}: {count}" for column, count in missing.items() if count]
            if details:
                return f"{table_name} has {total_missing} missing values. " + "; ".join(details)
            return f"{table_name} has no missing values."

        if intent_name == "profile_table" and table_name:
            profile = profile_table(connection, table_name)
            return (
                f"{profile['table']}: {profile['rows']} rows, {len(profile['columns'])} columns, "
                f"{profile['missing_total']} missing values."
            )

    if intent_name == "unsupported":
        return "I can handle tables, row counts, columns, missing values, and basic profiling summaries."

    return "I could not map that question to a simple supported check."


st.title("AI Data Analyst")
st.write("Ask simple data-quality questions about the ingested datasets.")

datasets = list_datasets()
if not datasets:
    st.info("Upload an Excel file in Data Management first.")
    st.stop()

use_all = st.checkbox("Use all datasets", value=st.session_state.get("use_all_datasets", False))
st.session_state.use_all_datasets = use_all

if use_all:
    selected_datasets = datasets
else:
    selected_datasets = st.multiselect(
        "Choose datasets",
        datasets,
        default=st.session_state.get("selected_datasets", datasets[:1]),
    )
    st.session_state.selected_datasets = selected_datasets

selected_tables = tables_for_datasets(selected_datasets)

if selected_tables:
    st.caption("Selected datasets: " + ", ".join(selected_datasets))
else:
    st.info("Select at least one dataset.")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

question = st.chat_input("Ask about the selected datasets")
if question:
    if not selected_tables:
        st.warning("Select at least one dataset first.")
    else:
        st.session_state.messages.append({"role": "user", "content": question})
        answer = answer_question(question, selected_tables)
        st.session_state.messages.append({"role": "assistant", "content": answer})
        st.rerun()
