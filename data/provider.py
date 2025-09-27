# provider.py
# DataProvider interface and OptionAProvider (manual/CSV) for now
import pandas as pd
import os

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
        self.polygon_key = os.environ.get("POLYGON_KEY")
        self.fred_key = os.environ.get("FRED_KEY")

    def get_prices(self, ticker):
        # Fetch latest price and volume from Polygon.io
        url = f"https://api.polygon.io/v2/aggs/ticker/{ticker}/prev"
        params = {"apiKey": self.polygon_key}
        try:
            response = requests.get(url, params=params)
            data = response.json()
            results = data.get("results", [])
            if not results:
                return {'Ticker': ticker, 'Price': None, 'ChgPct': None, 'Volume': None, 'AvgVol': None}
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
            return {'Ticker': ticker, 'Price': None, 'ChgPct': None, 'Volume': None, 'AvgVol': None}

    def get_historicals(self, ticker):
        # Fetch last 30 closes from Polygon.io
        url = f"https://api.polygon.io/v2/aggs/ticker/{ticker}/range/1/day/2024-01-01/2025-12-31"
        params = {"apiKey": self.polygon_key, "limit": 30}
        try:
            response = requests.get(url, params=params)
            data = response.json()
            closes = [bar['c'] for bar in data.get('results', [])][-30:]
            return pd.Series(closes)
        except Exception:
            return pd.Series([])

    def get_option_chain(self, ticker):
        # Placeholder: implement live option chain fetch if needed
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
