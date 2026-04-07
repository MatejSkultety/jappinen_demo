import streamlit as st

from src.ingest import list_datasets, tables_for_datasets
from src.llm_chat import ask_data_question


st.title("AI Data Analyst")
st.write("Ask simple data-quality questions about the ingested datasets.")

if st.button("Reset conversation"):
    st.session_state.messages = []
    st.rerun()

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
        answer = ask_data_question(question, selected_tables, st.session_state.messages[:-1])
        st.session_state.messages.append({"role": "assistant", "content": answer})
        st.rerun()
