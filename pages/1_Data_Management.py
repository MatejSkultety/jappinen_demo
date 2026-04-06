import streamlit as st

from src.file_store import delete_uploaded_file, list_uploaded_files, save_uploaded_file


st.title("Data Management")
st.write("Upload, list, and delete Excel files used by the app.")

uploaded_file = st.file_uploader("Upload .xlsx file", type=["xlsx"])
if uploaded_file is not None and st.button("Save file"):
    save_uploaded_file(uploaded_file)
    st.success("File uploaded.")
    st.rerun()

st.subheader("Uploaded files")
files = list_uploaded_files()
if not files:
    st.info("No files uploaded yet.")
else:
    for file_name in files:
        left, right = st.columns([5, 1])
        left.write(file_name)
        if right.button("Delete", key=f"delete_{file_name}"):
            delete_uploaded_file(file_name)
            st.rerun()