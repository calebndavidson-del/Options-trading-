# ticker_page.py
# Per-ticker options and Greeks table using yfinance and mibian


import streamlit as st
import pandas as pd
import requests
import os
import yfinance as yf
from logic.greeks import calculate_greeks
import datetime

# Add periodic refresh every 60 seconds
st_autorefresh = st.experimental_rerun if hasattr(st, 'experimental_rerun') else None
refresh_interval = 60 * 1000  # 60 seconds in ms
if hasattr(st, 'autorefresh'):
    st.autorefresh(interval=refresh_interval, key="polygon_refresh")

st.title("Per-Ticker Options & Greeks")


POLYGON_KEY = os.environ.get("POLYGON_KEY")

ticker = st.selectbox("Select Ticker", ["NVDA", "TSLA", "AMD", "META", "SPY", "QQQ"])

# Fetch option snapshot from Polygon.io
def fetch_polygon_options(ticker):
    url = f"https://api.polygon.io/v3/snapshot/options/{ticker.upper()}"
    params = {"apiKey": POLYGON_KEY}
    all_options = []
    try:
        while url:
            response = requests.get(url, params=params)
            data = response.json()
            if 'results' in data and 'options' in data['results']:
                for opt in data['results']['options']:
                    # Flatten greeks if present
                    greeks = opt.pop('greeks', {}) if 'greeks' in opt and isinstance(opt['greeks'], dict) else {}
                    for k, v in greeks.items():
                        opt[k] = v
                    all_options.append(opt)
            # Check for pagination
            url = data.get('next_url')
            params = {}  # next_url already contains the apiKey
        return all_options
    except Exception as e:
        st.error(f"Polygon API error: {e}")
        return []


options = fetch_polygon_options(ticker)
df = pd.DataFrame(options)
if not df.empty:
    calls = df[df['type'].str.lower() == 'call']
    # Use last price as underlying
    underlying_price = df['underlying_price'].iloc[0] if 'underlying_price' in df.columns else None
    if underlying_price is not None:
        calls['abs_diff'] = (calls['strike_price'] - underlying_price).abs()
        calls = calls.sort_values('abs_diff')
        shortlist = calls.head(3)
    else:
        shortlist = calls.head(3)
    # Fill Greeks: use Polygon if present, else calculate
    interest_rate = 0.05
    greeks_cols = ['delta', 'gamma', 'theta', 'vega']
    for idx, row in shortlist.iterrows():
        missing_greeks = any(pd.isna(row.get(col)) for col in greeks_cols)
        if missing_greeks:
            # Calculate using Black-Scholes if any Greek is missing
            # Use yfinance for IV if missing
            try:
                ytkr = yf.Ticker(ticker)
                expiries = ytkr.options
                expiry = row['expiration_date'] if 'expiration_date' in row else (expiries[0] if expiries else None)
                days_to_expiry = (datetime.datetime.strptime(str(expiry), "%Y-%m-%d").date() - datetime.datetime.now().date()).days if expiry else 30
                iv = row['implied_volatility'] * 100 if not pd.isna(row.get('implied_volatility')) else 30.0
                greeks = calculate_greeks(
                    underlying_price=float(underlying_price) if underlying_price is not None else float(row['strike_price']),
                    strike_price=float(row['strike_price']),
                    interest_rate=interest_rate,
                    days_to_expiry=int(days_to_expiry),
                    implied_volatility=iv
                )
                for g in greeks_cols:
                    shortlist.at[idx, g] = greeks[g]
            except Exception as e:
                pass
    display_cols = ['strike_price', 'bid', 'ask', 'implied_volatility', 'delta', 'theta', 'gamma', 'vega', 'open_interest', 'volume', 'expiration_date']
    shortlist = shortlist[display_cols] if all(col in shortlist.columns for col in display_cols) else shortlist
    shortlist = shortlist.rename(columns={
        'strike_price': 'Strike',
        'bid': 'Bid',
        'ask': 'Ask',
        'implied_volatility': 'IV',
        'delta': 'Delta',
        'theta': 'Theta',
        'gamma': 'Gamma',
        'vega': 'Vega',
        'open_interest': 'OI',
        'volume': 'Volume',
        'expiration_date': 'Expiry'
    })
    st.dataframe(shortlist, use_container_width=True)
else:
    st.warning("No option data available from Polygon.io for this ticker.")
