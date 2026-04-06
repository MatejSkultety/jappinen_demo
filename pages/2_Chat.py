import json

import pandas as pd
import streamlit as st
from openai import OpenAI

from src.config import OPENAI_API_KEY
from src.db import get_connection, table_columns, table_row_count
from src.file_store import list_uploaded_files
from src.ingest import ingest_excel_file, tables_for_file
from src.profiling import file_table_summaries, missing_values_by_column, profile_table


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


def answer_question(question: str, file_name: str) -> str:
    tables = tables_for_file(file_name)
    if not tables:
        return "No tables were created for this file yet."

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
st.write("Use Data Management to upload Excel files, then open Chat to ask simple data-quality questions.")

files = list_uploaded_files()
if not files:
    st.info("Upload an Excel file in Data Management first.")
    st.stop()

selected_file = st.selectbox("Choose an uploaded file", files)
if st.button("Load file into SQLite"):
    ingest_excel_file(selected_file)
    st.session_state.active_file = selected_file
    st.success("File loaded into SQLite.")
    st.rerun()

active_file = st.session_state.get("active_file")
if active_file not in files:
    active_file = None

if active_file:
    st.caption(f"Active file: {active_file}")
    summaries = file_table_summaries(active_file)
    if summaries:
        st.subheader("Available tables")
        st.dataframe(pd.DataFrame(summaries), use_container_width=True, hide_index=True)
    else:
        st.info("Load the file to create tables.")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

question = st.chat_input("Ask about the selected file")
if question:
    if not active_file:
        st.warning("Load a file first.")
    else:
        st.session_state.messages.append({"role": "user", "content": question})
        answer = answer_question(question, active_file)
        st.session_state.messages.append({"role": "assistant", "content": answer})
        st.rerun()
