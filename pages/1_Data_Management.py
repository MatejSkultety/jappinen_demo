import streamlit as st

from src.ingest import delete_dataset, ingest_excel_file, list_datasets, tables_for_dataset


st.title("Data Management")
st.write("Upload an Excel file and ingest it directly into SQLite.")

uploaded_file = st.file_uploader("Upload .xlsx file", type=["xlsx"])
if uploaded_file is not None and st.button("Ingest file"):
    dataset_name = ingest_excel_file(uploaded_file)
    st.success(f"Ingested {dataset_name}.")
    st.rerun()

st.subheader("Ingested datasets")
datasets = list_datasets()
if not datasets:
    st.info("No datasets yet.")
else:
    for dataset_name in datasets:
        left, right = st.columns([5, 1])
        left.write(f"{dataset_name} ({len(tables_for_dataset(dataset_name))} tables)")
        if right.button("Delete", key=f"delete_{dataset_name}"):
            delete_dataset(dataset_name)
            st.rerun()