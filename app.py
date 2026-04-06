import streamlit as st


st.set_page_config(page_title="AI Data Analyst", layout="wide")

pages = st.navigation(
	[
		st.Page("pages/2_Chat.py", title="Chat"),
		st.Page("pages/1_Data_Management.py", title="Data Management"),
	]
)

pages.run()