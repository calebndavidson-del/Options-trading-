

import streamlit as st

import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
import datetime

st.title('Options Dashboard: Top 100 US Stocks (Yahoo Finance)')
st.caption('Scanning for best call options by strict rubric. Data: Yahoo Finance (15m delayed)')

# Top 100 US stocks by market cap (example, can be replaced with dynamic list)
TICKERS = [
    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'BRK-B', 'UNH', 'LLY', 'JPM', 'V', 'XOM', 'MA', 'AVGO', 'JNJ', 'PG', 'HD', 'MRK', 'COST',
    'ABBV', 'CVX', 'ADBE', 'PEP', 'KO', 'WMT', 'CRM', 'MCD', 'BAC', 'TMO', 'DIS', 'CSCO', 'ACN', 'ABT', 'LIN', 'DHR', 'VZ', 'NFLX', 'NKE', 'TXN', 'NEE',
    'WFC', 'AMD', 'BMY', 'PM', 'AMGN', 'INTC', 'LOW', 'QCOM', 'HON', 'UNP', 'RTX', 'SBUX', 'IBM', 'MDT', 'CAT', 'GS', 'GE', 'BLK', 'ISRG', 'AMT', 'SPGI',
    'PLD', 'T', 'CVS', 'LMT', 'SYK', 'ZTS', 'NOW', 'DE', 'ADP', 'MO', 'GILD', 'MDLZ', 'AXP', 'BKNG', 'C', 'SCHW', 'CB', 'MMC', 'CI', 'SO', 'USB', 'TGT',
    'DUK', 'PNC', 'ELV', 'CL', 'SHW', 'APD', 'BDX', 'ICE', 'NSC', 'ITW', 'FDX', 'GM', 'ADI', 'EW', 'REGN', 'AON', 'ETN', 'EMR'
]

# Table columns (as per user spec)
COLUMNS = [
    "Ticker", "Price", "%chg", "Vol", "AvgVol", "VolRatio", "20EMA", "50EMA", "200SMA", "MA Trend", "VWAP", "RSI", "MACD", "Key S/R", "Target Expiry", "Suggested Strike", "Bid–Ask", "Delta", "Theta", "Gamma", "IV", "OI", "Breakeven", "POP", "Sentiment Score", "Signal Score", "Signal", "Reason", "Timestamp"
]

def get_option_candidates(ticker):
    try:
        yf_ticker = yf.Ticker(ticker)
        price = yf_ticker.history(period="1d")['Close'].iloc[-1]
        hist = yf_ticker.history(period="1y")
        avg_vol = hist['Volume'].tail(30).mean() if not hist.empty else np.nan
        today_vol = hist['Volume'].iloc[-1] if not hist.empty else np.nan
        vol_ratio = today_vol / avg_vol if avg_vol and avg_vol > 0 else np.nan
        ema_20 = hist['Close'].ewm(span=20).mean().iloc[-1] if len(hist) >= 20 else np.nan
        ema_50 = hist['Close'].ewm(span=50).mean().iloc[-1] if len(hist) >= 50 else np.nan
        sma_200 = hist['Close'].rolling(window=200).mean().iloc[-1] if len(hist) >= 200 else np.nan
        ma_trend = 'Bullish' if ema_20 > ema_50 > sma_200 else ('Bearish' if ema_20 < ema_50 < sma_200 else 'Neutral')
        rsi = (100 - (100 / (1 + (hist['Close'].diff().dropna().gt(0).sum() / hist['Close'].diff().dropna().lt(0).sum())))) if len(hist) >= 14 else np.nan
        macd_line = hist['Close'].ewm(span=12).mean() - hist['Close'].ewm(span=26).mean() if len(hist) >= 26 else np.nan
        macd = 'Up' if macd_line.iloc[-1] > 0 else 'Down' if not pd.isna(macd_line.iloc[-1]) else np.nan
        vwap = np.nan  # Yahoo Finance does not provide intraday VWAP
        # Get options chain for nearest expiry
        expiries = yf_ticker.options
        if not expiries:
            return []
        expiry = expiries[0]
        opt_chain = yf_ticker.option_chain(expiry)
        calls = opt_chain.calls
        # ATM ±2 strikes
        calls['abs_diff'] = (calls['strike'] - price).abs()
        atm_calls = calls.sort_values('abs_diff').head(5)
        results = []
        for _, row in atm_calls.iterrows():
            # Apply strict rubric
            delta = row.get('delta', np.nan)
            theta = row.get('theta', np.nan)
            gamma = row.get('gamma', np.nan)
            iv = row.get('impliedVolatility', np.nan) * 100 if not pd.isna(row.get('impliedVolatility', np.nan)) else np.nan
            oi = row.get('openInterest', np.nan)
            bid = row.get('bid', np.nan)
            ask = row.get('ask', np.nan)
            mid = (bid + ask) / 2 if not pd.isna(bid) and not pd.isna(ask) else np.nan
            spread_pct = (ask - bid) / mid if mid and mid > 0 else np.nan
            dte = (pd.to_datetime(expiry) - pd.Timestamp.now()).days
            # Strict filter
            if not (0.45 <= delta <= 0.60):
                continue
            if theta < -0.03:
                continue
            if not (0.005 <= gamma <= 0.015):
                continue
            if not (20 <= iv <= 55):
                continue
            if oi < 1000:
                continue
            if spread_pct > 0.05:
                continue
            # Compose row
            results.append([
                ticker, price, np.nan, today_vol, avg_vol, vol_ratio, ema_20, ema_50, sma_200, ma_trend, vwap, rsi, macd, '', expiry, row['strike'], f"{bid} × {ask}", delta, theta, gamma, iv, oi, '', '', '', '', '', '', '', pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')
            ])
        return results
    except Exception as e:
        return []

# Scan all tickers and collect best calls
all_candidates = []
for ticker in TICKERS:
    all_candidates.extend(get_option_candidates(ticker))

 

df = pd.DataFrame(all_candidates, columns=COLUMNS)
st.dataframe(df, use_container_width=True)

