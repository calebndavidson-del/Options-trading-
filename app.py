
# app.py
import streamlit as st
from pages import dashboard

PAGES = {
    "Dashboard": dashboard,
    # TODO: Add NVDA, TSLA, AMD, META, SPY, QQQ, Signals Log, Sentiment, Levels, Config
}

st.sidebar.title("Navigation")
selection = st.sidebar.radio("Go to", list(PAGES.keys()))
PAGES[selection]
