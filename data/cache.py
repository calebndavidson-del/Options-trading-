# cache.py
# Caching wrappers for Streamlit
import streamlit as st
from datetime import timedelta

@st.cache_data(ttl=60)
def get_prices(ticker, provider):
    return provider.get_prices(ticker)

@st.cache_data(ttl=60)
def get_historicals(ticker, provider):
    return provider.get_historicals(ticker)

@st.cache_data(ttl=300)
def get_sentiment(provider):
    return provider.get_sentiment()
