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
        self.alpha_vantage_key = os.environ.get("ALPHA_VANTAGE")

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
            url = f"https://api.polygon.io/v2/aggs/ticker/{ticker}/range/1/day/2023-01-01/2025-12-31"
            params = {"apiKey": self.polygon_key, "limit": 220}
            try:
                response = requests.get(url, params=params)
                data = response.json()
                closes = [bar['c'] for bar in data.get('results', [])][-220:]
                if closes:
                    return pd.Series(closes)
            except Exception:
                pass
        # Fallback to yfinance
        try:
            yf_ticker = yf.Ticker(ticker)
            hist = yf_ticker.history(period="2y")
            closes = hist['Close'].tolist()[-400:]
            return pd.Series(closes)
        except Exception:
            return pd.Series([])

    def get_option_chain(self, ticker):
        # Try Alpha Vantage
        av_url = f'https://www.alphavantage.co/query'
        av_params = {
            'function': 'OPTION_CHAIN',
            'symbol': ticker,
            'apikey': self.alpha_vantage_key
        }
        av_options = None
        try:
            av_resp = requests.get(av_url, params=av_params, timeout=10)
            av_data = av_resp.json()
            if 'optionChain' in av_data:
                calls = pd.DataFrame(av_data['optionChain'].get('calls', []))
                puts = pd.DataFrame(av_data['optionChain'].get('puts', []))
                if not calls.empty:
                    calls['type'] = 'call'
                if not puts.empty:
                    puts['type'] = 'put'
                av_options = pd.concat([calls, puts], ignore_index=True)
        except Exception:
            av_options = None

        # Try yfinance
        yf_options = None
        try:
            yf_ticker = yf.Ticker(ticker)
            expiries = yf_ticker.options
            if expiries:
                expiry = expiries[0]
                opt_chain = yf_ticker.option_chain(expiry)
                calls = opt_chain.calls
                puts = opt_chain.puts
                calls['expiry'] = expiry
                puts['expiry'] = expiry
                yf_options = pd.concat([calls, puts], ignore_index=True)
        except Exception:
            yf_options = None

        # Cross-check and merge
        if av_options is not None and not av_options.empty:
            if yf_options is not None and not yf_options.empty:
                # Merge on strike and type, prefer IV from AV if both present, else average
                merged = pd.merge(av_options, yf_options, on=['strike', 'type'], suffixes=('_av', '_yf'), how='outer')
                def pick_iv(row):
                    ivs = []
                    if not pd.isna(row.get('impliedVolatility_av')):
                        ivs.append(row['impliedVolatility_av'])
                    if not pd.isna(row.get('impliedVolatility_yf')):
                        ivs.append(row['impliedVolatility_yf']*100 if row['impliedVolatility_yf'] < 2 else row['impliedVolatility_yf'])
                    if ivs:
                        return sum(ivs)/len(ivs)
                    return None
                merged['impliedVolatility'] = merged.apply(pick_iv, axis=1)
                merged['expiry'] = merged['expiry_av'].combine_first(merged['expiry_yf'])
                # Keep only relevant columns
                return merged[['strike', 'type', 'impliedVolatility', 'expiry']].dropna(subset=['strike'])
            else:
                return av_options[['strike', 'type', 'impliedVolatility', 'expiry']] if 'expiry' in av_options.columns else av_options[['strike', 'type', 'impliedVolatility']]
        elif yf_options is not None and not yf_options.empty:
            yf_options = yf_options.rename(columns={'contractType': 'type'})
            return yf_options[['strike', 'type', 'impliedVolatility', 'expiry']]
        else:
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
