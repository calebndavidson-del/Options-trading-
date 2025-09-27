
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


from data.provider import OptionAProvider
provider = OptionAProvider()


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
            print(f"[DEBUG] Skipping {ticker}: no historical data from yfinance. closes={closes}")
            continue  # Skip tickers with no data
        if len(closes) >= 200:
            ema_20 = ema(closes, 20).iloc[-1]
            ema_50 = ema(closes, 50).iloc[-1]
            sma_200 = sma(closes, 200).iloc[-1]
            if ema_20 > ema_50 > sma_200:
                ma_trend = 'Bullish'
            elif ema_20 < ema_50 < sma_200:
                ma_trend = 'Bearish'
            else:
                ma_trend = 'Neutral'
        else:
            ema_20 = ema(closes, 20).iloc[-1] if len(closes) >= 20 else None
            ema_50 = ema(closes, 50).iloc[-1] if len(closes) >= 50 else None
            sma_200 = None
            ma_trend = ''
        rsi_val = rsi(closes).iloc[-1]
        macd_line, macd_signal = macd(closes)
        macd_val = 'Up' if macd_line.iloc[-1] > macd_signal.iloc[-1] else 'Down'
        vol_ratio_val = vol_ratio(today_vol, avg_30_vol) if today_vol and avg_30_vol else None

        # Get real option chain data for this ticker
        option_chain = provider.get_option_chain(ticker)

        # Only show the ATM strike for each ticker, and append one row per ticker
        strike_price = None
        expiry = ''
        implied_volatility = price_row.get('IV', 48)
        days_to_expiry = price_row.get('DTE', 21)
        if isinstance(option_chain, pd.DataFrame) and not option_chain.empty:
            strikes = sorted(option_chain['strike'].unique())
            if strikes:
                atm_idx = min(range(len(strikes)), key=lambda i: abs(strikes[i] - price_row['Price']))
                strike_price = strikes[atm_idx]
                opt_row = option_chain[option_chain['strike'] == strike_price].iloc[0]
                expiry = opt_row['expiry'] if 'expiry' in opt_row else opt_row.get('expiration', '')
                iv_val = opt_row.get('impliedVolatility', 0)
                implied_volatility = iv_val * 100 if iv_val < 2 else iv_val
                days_to_expiry = (pd.to_datetime(expiry) - pd.Timestamp.now()).days if expiry else 21
        else:
            strike_price = price_row.get('Strike', 180)

        underlying_price = price_row['Price']
        interest_rate = 0.05
        print(f"[DEBUG] {ticker} Greeks inputs: price={underlying_price}, strike={strike_price}, rate={interest_rate}, dte={days_to_expiry}, iv={implied_volatility}")
        greeks = None
        # Try Polygon API for Greeks first
        if expiry and strike_price:
            greeks = provider.get_greeks(ticker, expiry=expiry, strike=strike_price, opt_type='call')
            print(f"[DEBUG] {ticker} Polygon Greeks: {greeks}")
        # Fallback to Black-Scholes if Polygon fails or returns None
        if not greeks or all(greeks.get(k) in [None, ''] for k in ['delta', 'theta', 'gamma']):
            if all(x is not None and x != 0 for x in [underlying_price, strike_price, implied_volatility, days_to_expiry]):
                greeks = calculate_greeks(underlying_price, strike_price, interest_rate, days_to_expiry, implied_volatility)
                print(f"[DEBUG] {ticker} Fallback BS Greeks: {greeks}")
            else:
                print(f"[WARN] {ticker} missing Greeks input: price={underlying_price}, strike={strike_price}, dte={days_to_expiry}, iv={implied_volatility}")
                greeks = {'delta': '', 'theta': '', 'gamma': ''}

        tech_score = 0  # TODO: compute
        greeks_score = 0  # TODO: compute
        sent_score = 0  # TODO: compute
        dte_score = 0  # TODO: compute
        comp_score = composite_score(tech_score, greeks_score, sent_score, dte_score)
        signal = signal_from_score(comp_score, greeks.get('theta', 0), days_to_expiry)
        reason = price_row.get('Reason', '')
        timestamp = pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')
        data_dict[ticker] = [
            ticker, price_row['Price'], price_row['ChgPct'], today_vol, avg_30_vol, vol_ratio_val, ema_20, ema_50, sma_200, ma_trend, rsi_val, macd_val, price_row.get('KeySR', ''), expiry, strike_price, price_row.get('BidAsk', ''),
            greeks.get('delta', ''), greeks.get('theta', ''), greeks.get('gamma', ''), implied_volatility, price_row.get('OI', ''), price_row.get('Breakeven', ''), price_row.get('POP', ''), sent_score, comp_score, signal, reason, timestamp
        ]
    return data_dict

columns = ["Ticker", "Price", "%chg", "Vol", "AvgVol", "VolRatio", "20EMA", "50EMA", "200SMA", "MA Trend", "RSI", "MACD", "Key S/R", "Target Expiry", "Suggested Strike", "Bid–Ask", "Delta", "Theta", "Gamma", "IV", "OI", "Breakeven", "POP", "Sentiment Score", "Signal Score", "Signal", "Reason", "Timestamp"]
data_dict = build_data()
df = pd.DataFrame(list(data_dict.values()), columns=columns)
st.dataframe(df, width='stretch')
