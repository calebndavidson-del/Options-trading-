# provider.py
# DataProvider interface and OptionAProvider (manual/CSV) for now
import pandas as pd
import os
from dotenv import load_dotenv
import yfinance as yf

class DataProvider:
    def get_prices(self, ticker):
        raise NotImplementedError
    def get_historicals(self, ticker):
        raise NotImplementedError
    def get_option_chain(self, ticker):
        raise NotImplementedError
    def get_sentiment(self):
        raise NotImplementedError

import requests

class OptionAProvider(DataProvider):
    def __init__(self):
        load_dotenv()
        self.polygon_key = os.environ.get("POLYGON_KEY")
        self.fred_key = os.environ.get("FRED_KEY")

    def get_prices(self, ticker):
        # Try Polygon API first if key is present
        if self.polygon_key:
            url = f"https://api.polygon.io/v2/aggs/ticker/{ticker}/prev"
            params = {"apiKey": self.polygon_key}
            try:
                response = requests.get(url, params=params)
                data = response.json()
                results = data.get("results", [])
                if results:
                    result = results[0]
                    return {
                        'Ticker': ticker,
                        'Price': result['c'],
                        'ChgPct': round((result['c'] - result['o']) / result['o'] * 100, 2) if result['o'] else 0,
                        'Volume': result['v'],
                        'AvgVol': result.get('av', result['v']),
                        'Strike': None,
                        'DTE': 21,
                        'IV': 48,
                        'KeySR': '',
                        'Expiry': '',
                        'BidAsk': '',
                        'OI': '',
                        'Breakeven': '',
                        'POP': '',
                        'Reason': ''
                    }
            except Exception:
                pass
        # Fallback to yfinance
        try:
            yf_ticker = yf.Ticker(ticker)
            hist = yf_ticker.history(period="2d")
            if hist.empty:
                return {'Ticker': ticker, 'Price': None, 'ChgPct': None, 'Volume': None, 'AvgVol': None}
            last = hist.iloc[-1]
            prev = hist.iloc[-2] if len(hist) > 1 else last
            chg_pct = round((last['Close'] - prev['Close']) / prev['Close'] * 100, 2) if prev['Close'] else 0
            avg_vol = hist['Volume'].mean()
            return {
                'Ticker': ticker,
                'Price': last['Close'],
                'ChgPct': chg_pct,
                'Volume': last['Volume'],
                'AvgVol': avg_vol,
                'Strike': None,
                'DTE': 21,
                'IV': 48,
                'KeySR': '',
                'Expiry': '',
                'BidAsk': '',
                'OI': '',
                'Breakeven': '',
                'POP': '',
                'Reason': ''
            }
        except Exception:
            return {'Ticker': ticker, 'Price': None, 'ChgPct': None, 'Volume': None, 'AvgVol': None}

    def get_historicals(self, ticker):
        # Try Polygon API first if key is present
        if self.polygon_key:
            url = f"https://api.polygon.io/v2/aggs/ticker/{ticker}/range/1/day/2024-01-01/2025-12-31"
            params = {"apiKey": self.polygon_key, "limit": 30}
            try:
                response = requests.get(url, params=params)
                data = response.json()
                closes = [bar['c'] for bar in data.get('results', [])][-30:]
                if closes:
                    return pd.Series(closes)
            except Exception:
                pass
        # Fallback to yfinance
        try:
            yf_ticker = yf.Ticker(ticker)
            hist = yf_ticker.history(period="1mo")
            closes = hist['Close'].tolist()[-30:]
            return pd.Series(closes)
        except Exception:
            return pd.Series([])

    def get_option_chain(self, ticker):
        # Use yfinance to fetch option chain for the nearest expiry
        try:
            yf_ticker = yf.Ticker(ticker)
            expiries = yf_ticker.options
            if not expiries:
                return []
            expiry = expiries[0]  # nearest expiry
            opt_chain = yf_ticker.option_chain(expiry)
            calls = opt_chain.calls
            puts = opt_chain.puts
            # Add expiry to each row
            calls['expiry'] = expiry
            puts['expiry'] = expiry
            # Combine calls and puts
            options = pd.concat([calls, puts], ignore_index=True)
            return options
        except Exception:
            return []

    def get_sentiment(self):
        # Example: fetch VIX from FRED
        url = "https://api.stlouisfed.org/fred/series/observations"
        params = {
            "series_id": "VIXCLS",
            "api_key": self.fred_key,
            "file_type": "json"
        }
        try:
            response = requests.get(url, params=params)
            data = response.json()
            observations = data.get("observations", [])
            if not observations:
                return {"VIX": None}
            latest = observations[-1]["value"]
            return {"VIX": latest}
        except Exception:
            return {"VIX": None}
