

from polygon_ws import start_ws_thread, get_latest_ws_data, close_ws
import streamlit as st

# Display latest real-time data from WebSocket
st.subheader("Real-Time Option Trades (Polygon.io WebSocket)")
latest_data = get_latest_ws_data()
if latest_data:
    for msg in latest_data[-10:]:
        st.json(msg)
else:
    st.write("No real-time data received yet.")


import streamlit as st
import requests
import os

# Load API keys from environment variables
FRED_KEY = os.environ.get("FRED_KEY")
POLYGON_KEY = "uz85txFQaRLRhVMNEwUfZr4wzIVcXgf0"

from data.provider import OptionAProvider
provider = OptionAProvider()
# Authenticate Polygon API key before anything else
polygon_ok, polygon_msg = provider.check_polygon_key()
if not polygon_ok:
    st.error(f"Polygon API authentication failed: {polygon_msg}")
    st.stop()

from logic.greeks import calculate_greeks
# dashboard.py
import streamlit as st
import pandas as pd



from data.cache import get_prices, get_historicals, get_sentiment
from logic.scoring import composite_score, signal_from_score
from logic.features import ema, sma, rsi, macd, vol_ratio


TICKERS = ['NVDA', 'TSLA', 'AMD', 'META', 'SPY', 'QQQ']

# Let user select ticker for WebSocket
selected_ticker = st.selectbox("Select Ticker for Live Data", TICKERS)

# Start WebSocket thread for selected ticker (only once per ticker)
if 'ws_started' not in st.session_state or st.session_state.get('ws_ticker') != selected_ticker:
    close_ws()  # Explicitly close any previous WebSocket before starting a new one
    start_ws_thread(selected_ticker)
    st.session_state['ws_started'] = True
    st.session_state['ws_ticker'] = selected_ticker

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



from data.provider import OptionAProvider
provider = OptionAProvider()

# Check Polygon API key connectivity and show status
polygon_ok, polygon_msg = provider.check_polygon_key()
if polygon_ok:
    st.success(f"Polygon API: {polygon_msg}")
else:
    st.error(f"Polygon API: {polygon_msg}")


# Build data_dict locally to avoid global accumulation across reruns

import yfinance as yf

def build_data():
    data_dict = {}
    for ticker in TICKERS:
        price_row = get_prices(ticker)
        # Always use yfinance for historicals to match price source
        try:
            yf_ticker = yf.Ticker(ticker)
            hist = yf_ticker.history(period="1y")
            closes = hist['Close'] if not hist.empty else []
            print(f"[DEBUG] {ticker} closes length: {len(closes)} sample: {closes[:5] if hasattr(closes, '__getitem__') else closes}")
            # VolRatio calculation: use last day's volume and 30-day avg (filter for nonzero, non-NaN)
            if not hist.empty:
                today_vol = hist['Volume'].iloc[-1]
                last_30_vols = hist['Volume'][~hist['Volume'].isna() & (hist['Volume'] > 0)].tail(30)
                avg_30_vol = last_30_vols.mean() if len(last_30_vols) > 0 else None
                print(f"[DEBUG] {ticker} last 30 vols: {list(last_30_vols)} avg_30_vol: {avg_30_vol}")
            else:
                today_vol = None
                avg_30_vol = None
        except Exception as e:
            print(f"[DEBUG] {ticker} yfinance error: {e}")
            closes = []
            today_vol = None
            avg_30_vol = None
        if closes is None or len(closes) == 0:
            print(f"[DEBUG] {ticker}: No historical data from yfinance. Row will still be added with missing values.")
        # Defensive: always define all variables used in row
        ema_20 = ema(closes, 20).iloc[-1] if closes is not None and len(closes) >= 20 else None
        ema_50 = ema(closes, 50).iloc[-1] if closes is not None and len(closes) >= 50 else None
        sma_200 = sma(closes, 200).iloc[-1] if closes is not None and len(closes) >= 200 else None
        ma_trend = ''
        if ema_20 and ema_50 and sma_200:
            if ema_20 > ema_50 > sma_200:
                ma_trend = 'Bullish'
            elif ema_20 < ema_50 < sma_200:
                ma_trend = 'Bearish'
            else:
                ma_trend = 'Neutral'
        rsi_val = rsi(closes).iloc[-1] if closes is not None and len(closes) >= 14 else None
        macd_line, macd_signal = macd(closes) if closes is not None and len(closes) >= 26 else (None, None)
        macd_val = 'Up' if macd_line is not None and macd_signal is not None and macd_line.iloc[-1] > macd_signal.iloc[-1] else ('Down' if macd_line is not None and macd_signal is not None else None)
        vol_ratio_val = vol_ratio(today_vol, avg_30_vol) if today_vol is not None and avg_30_vol is not None else None


        # --- Always use yfinance for ATM option and Greeks ---
        try:
            yf_ticker = yf.Ticker(ticker)
            expirations = yf_ticker.options
            expiry = expirations[0] if expirations else (pd.Timestamp.now() + pd.Timedelta(days=21)).strftime('%Y-%m-%d')
            opt_chain = yf_ticker.option_chain(expiry)
            calls = opt_chain.calls
            underlying_price = price_row['Price']
            if not calls.empty:
                atm_strike = min(calls['strike'], key=lambda x: abs(x - underlying_price))
                atm_row = calls[calls['strike'] == atm_strike].iloc[0]
                strike_price = atm_row['strike']
                bid = atm_row['bid']
                ask = atm_row['ask']
                iv = atm_row['impliedVolatility'] * 100 if not pd.isna(atm_row['impliedVolatility']) else 0
                days_to_expiry = (pd.to_datetime(expiry) - pd.Timestamp.now()).days
                greeks = calculate_greeks(underlying_price, strike_price, 0.05, days_to_expiry, iv)
                bid_ask = f"{bid}/{ask}"
                implied_volatility = iv
            else:
                strike_price = bid = ask = iv = days_to_expiry = None
                greeks = {'delta': None, 'theta': None, 'gamma': None, 'vega': None}
                bid_ask = ''
        except Exception as e:
            print(f"[YFINANCE CHAIN ERROR] {ticker}: {e}")
            strike_price = bid = ask = iv = days_to_expiry = None
            greeks = {'delta': None, 'theta': None, 'gamma': None, 'vega': None}
            bid_ask = ''

        tech_score = 0  # TODO: compute
        greeks_score = 0  # TODO: compute
        sent_score = 0  # TODO: compute
        dte_score = 0  # TODO: compute
        comp_score = composite_score(tech_score, greeks_score, sent_score, dte_score)
        signal = signal_from_score(comp_score, greeks.get('theta', 0), days_to_expiry)
        reason = price_row.get('Reason', '')
        timestamp = pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')
        data_dict[ticker] = [
            ticker, price_row['Price'], price_row['ChgPct'], today_vol, avg_30_vol, vol_ratio_val, ema_20, ema_50, sma_200, ma_trend, rsi_val, macd_val, price_row.get('KeySR', ''), expiry, strike_price, bid_ask,
            greeks.get('delta', ''), greeks.get('theta', ''), greeks.get('gamma', ''), implied_volatility, price_row.get('OI', ''), price_row.get('Breakeven', ''), price_row.get('POP', ''), sent_score, comp_score, signal, reason, timestamp
        ]
    return data_dict

columns = ["Ticker", "Price", "%chg", "Vol", "AvgVol", "VolRatio", "20EMA", "50EMA", "200SMA", "MA Trend", "RSI", "MACD", "Key S/R", "Target Expiry", "Suggested Strike", "Bid–Ask", "Delta", "Theta", "Gamma", "IV", "OI", "Breakeven", "POP", "Sentiment Score", "Signal Score", "Signal", "Reason", "Timestamp"]
data_dict = build_data()
df = pd.DataFrame(list(data_dict.values()), columns=columns)
st.dataframe(df, width='stretch')
