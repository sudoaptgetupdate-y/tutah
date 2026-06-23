import streamlit as st
from streamlit_quill import st_quill

with st.form("test"):
    content = st_quill("Test")
    st.form_submit_button("Submit")
