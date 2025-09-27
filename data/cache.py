# cache.py
# Caching wrappers for Streamlit
import streamlit as st
from data.provider import OptionAProvider

@st.cache_data(ttl=60)
def get_prices(ticker):
    provider = OptionAProvider()
    return provider.get_prices(ticker)

@st.cache_data(ttl=60)
def get_historicals(ticker):
    provider = OptionAProvider()
    return provider.get_historicals(ticker)

@st.cache_data(ttl=300)
def get_sentiment():
    provider = OptionAProvider()
    return provider.get_sentiment()
