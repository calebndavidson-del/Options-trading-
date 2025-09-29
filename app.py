
# app.py
import streamlit as st
from pages import dashboard

from pages import ticker_page

PAGES = {
    "Dashboard": dashboard,
    "Ticker Page": ticker_page,
    # TODO: Add Signals Log, Sentiment, Levels, Config
}

st.sidebar.title("Navigation")
selection = st.sidebar.radio("Go to", list(PAGES.keys()))
PAGES[selection]
