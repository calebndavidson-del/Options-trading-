
import streamlit as st
import requests
import os

# Load API keys from environment variables
FRED_KEY = os.environ.get("FRED_KEY")
POLYGON_KEY = os.environ.get("POLYGON_KEY")

from logic.greeks import calculate_greeks
# dashboard.py
import streamlit as st
import pandas as pd
data = []

from data.cache import get_prices, get_historicals, get_sentiment
from logic.scoring import composite_score, signal_from_score
from logic.features import ema, sma, rsi, macd, vol_ratio

TICKERS = ['NVDA', 'TSLA', 'AMD', 'META', 'SPY', 'QQQ']

st.title('Options Trading Dashboard')
st.subheader('All Tickers Overview')


# Example: Pull VIX from FRED
def get_vix():
    url = "https://api.stlouisfed.org/fred/series/observations"
    params = {
        "series_id": "VIXCLS",
        "api_key": FRED_KEY,
        "file_type": "json"
    }
    try:
        response = requests.get(url, params=params)
        data = response.json()
        latest = data["observations"][-1]["value"]
        return latest
    except Exception:
        return "N/A"

# Example: Pull previous close from Polygon.io
def get_polygon_close(ticker):
    url = f"https://api.polygon.io/v2/aggs/ticker/{ticker}/prev"
    params = {"apiKey": POLYGON_KEY}
    try:
        response = requests.get(url, params=params)
        data = response.json()
        close = data["results"][0]["c"]
        return close
    except Exception:
        return "N/A"

# Top status bar
vix_val = get_vix()
market_clock = pd.Timestamp.now().strftime('%H:%M')
st.markdown(f"**Market Clock (ET):** {market_clock} | **VIX:** {vix_val} | **Put/Call:** N/A | **Fear & Greed:** N/A | **Macro:** N/A")


for ticker in TICKERS:
    price_row = get_prices(ticker)
    closes = get_historicals(ticker)
    ema_20 = ema(closes, 20).iloc[-1]
    ema_50 = ema(closes, 50).iloc[-1]
    sma_200 = sma(closes, 200).iloc[-1] if len(closes) >= 200 else None
    ma_trend = 'Bullish' if ema_20 > ema_50 > sma_200 else 'Bearish'
    rsi_val = rsi(closes).iloc[-1]
    macd_line, macd_signal = macd(closes)
    macd_val = 'Up' if macd_line.iloc[-1] > macd_signal.iloc[-1] else 'Down'
    vol_ratio_val = vol_ratio(price_row['Volume'], price_row['AvgVol'])
    # Example option contract data (replace with live API data)
    underlying_price = price_row['Price']
    strike_price = price_row.get('Strike', 180)
    interest_rate = 0.05
    days_to_expiry = price_row.get('DTE', 21)
    implied_volatility = price_row.get('IV', 48)  # as percentage
    greeks = calculate_greeks(underlying_price, strike_price, interest_rate, days_to_expiry, implied_volatility)
    # Signal scoring
    tech_score = 0  # TODO: compute
    greeks_score = 0  # TODO: compute
    sent_score = 0  # TODO: compute
    dte_score = 0  # TODO: compute
    comp_score = composite_score(tech_score, greeks_score, sent_score, dte_score)
    signal = signal_from_score(comp_score, greeks.get('theta', 0), days_to_expiry)
    reason = price_row.get('Reason', '')
    timestamp = pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')
    data.append([
        ticker, price_row['Price'], price_row['ChgPct'], price_row['Volume'], price_row['AvgVol'], vol_ratio_val, ema_20, ema_50, sma_200, ma_trend, rsi_val, macd_val, price_row.get('KeySR', ''), price_row.get('Expiry', ''), price_row.get('Strike', ''), price_row.get('BidAsk', ''),
        greeks.get('delta', ''), greeks.get('theta', ''), greeks.get('gamma', ''), price_row.get('IV', ''), price_row.get('OI', ''), price_row.get('Breakeven', ''), price_row.get('POP', ''), sent_score, comp_score, signal, reason, timestamp
    ])

columns = ["Ticker", "Price", "%chg", "Vol", "AvgVol", "VolRatio", "20EMA", "50EMA", "200SMA", "MA Trend", "RSI", "MACD", "Key S/R", "Target Expiry", "Suggested Strike", "Bid–Ask", "Delta", "Theta", "Gamma", "IV", "OI", "Breakeven", "POP", "Sentiment Score", "Signal Score", "Signal", "Reason", "Timestamp"]
df = pd.DataFrame(data, columns=columns)
st.dataframe(df, use_container_width=True)
