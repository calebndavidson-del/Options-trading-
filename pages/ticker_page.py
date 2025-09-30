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


POLYGON_KEY = "uz85txFQaRLRhVMNEwUfZr4wzIVcXgf0"

ticker = st.selectbox("Select Ticker", ["NVDA", "TSLA", "AMD", "META", "SPY", "QQQ"])

# Fetch option snapshot from Polygon.io
def fetch_polygon_options(ticker):
    url = f"https://api.polygon.io/v3/snapshot/options/{ticker.upper()}"
    params = {"apiKey": POLYGON_KEY}
    all_options = []
    try:
        while url:
            response = requests.get(url, params=params)
            try:
                data = response.json()
            except Exception as e:
                st.error(f"Polygon API response not JSON: {response.text}")
                return []
            # Handle 'results' as a list of options
            if 'results' in data and isinstance(data['results'], list):
                for opt in data['results']:
                    # Flatten greeks if present
                    greeks = opt.pop('greeks', {}) if 'greeks' in opt and isinstance(opt['greeks'], dict) else {}
                    for k, v in greeks.items():
                        opt[k] = v
                    # Flatten details
                    details = opt.pop('details', {}) if 'details' in opt and isinstance(opt['details'], dict) else {}
                    for k, v in details.items():
                        opt[k] = v
                    all_options.append(opt)
            # Check for pagination
            url = data.get('next_url')
            params = {"apiKey": POLYGON_KEY} if url else {}
        return all_options
    except Exception as e:
        st.error(f"Polygon API error: {e}")
        return []


options = fetch_polygon_options(ticker)
df = pd.DataFrame(options)
import numpy as np
if not df.empty:
    # Ensure 'bid' and 'ask' columns exist and filter out rows with missing values
    if 'bid' not in df.columns:
        df['bid'] = np.nan
    if 'ask' not in df.columns:
        df['ask'] = np.nan
    df = df.dropna(subset=['bid', 'ask'])
    # Only calls, only DTE 21-30, ATM ±2 strikes
    # Only calls, only DTE 21-30, ATM ±2 strikes
    today = datetime.datetime.now().date()
    df = df[df['contract_type'].str.lower() == 'call']
    df['DTE'] = (pd.to_datetime(df['expiration_date']) - pd.Timestamp(today)).dt.days
    df = df[(df['DTE'] >= 21) & (df['DTE'] <= 30)]
    # Underlying price for ATM filter
    underlying_price = df['underlying_asset.price'].iloc[0] if 'underlying_asset.price' in df.columns else None
    if underlying_price is not None:
        df['abs_diff'] = (df['strike_price'] - underlying_price).abs()
        df = df.sort_values('abs_diff')
        df = df[df['abs_diff'] <= 2 * (df['strike_price'].diff().abs().median() or 5)]  # ATM ±2 strikes
    # Filter by rubric
    df = df[(df['delta'] >= 0.45) & (df['delta'] <= 0.60)]
    df = df[(df['theta'] >= -0.03)]
    df = df[(df['gamma'] >= 0.005) & (df['gamma'] <= 0.015)]
    df = df[(df['implied_volatility'] >= 0.20) & (df['implied_volatility'] <= 0.55)]
    df = df[(df['open_interest'] >= (1000 if ticker not in ['SPY', 'QQQ'] else 5000))]
    # Calculate spread %
    df['mid'] = (df['bid'] + df['ask']) / 2
    df['spread_pct'] = (df['ask'] - df['bid']) / df['mid']
    df = df[df['spread_pct'] <= 0.05]
    # Show top 3 by OI
    shortlist = df.sort_values('open_interest', ascending=False).head(3)
    display_cols = ['strike_price', 'bid', 'ask', 'implied_volatility', 'delta', 'theta', 'gamma', 'vega', 'open_interest', 'volume', 'expiration_date', 'DTE', 'spread_pct']
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
        'expiration_date': 'Expiry',
        'DTE': 'DTE',
        'spread_pct': 'Spread %'
    })
    st.dataframe(shortlist, use_container_width=True)
else:
    st.warning("No option data available from Polygon.io for this ticker.")
