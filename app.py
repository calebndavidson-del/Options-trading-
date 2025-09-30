
# app.py
import streamlit as st
# Only import dashboard for main page; Streamlit will auto-discover pages in /pages
from pages import dashboard

st.sidebar.title("Navigation")
st.write("Use the sidebar to navigate. For more features, see the pages menu.")
dashboard
