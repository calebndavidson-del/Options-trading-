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

    def get_greeks(self, ticker, expiry=None, strike=None, opt_type='call'):
        """
        Fetch option greeks from Polygon API for a given ticker, expiry, strike, and type.
        """
        if not self.polygon_key or not expiry or not strike:
            return {'delta': None, 'gamma': None, 'theta': None, 'vega': None}
        # Polygon uses OCC option symbol format
        # Example: AAPL240920C00190000 (AAPL, 2024-09-20, Call, 190.00)
        # Format: {root}{YYMMDD}{C/P}{strike*1000:08d}
        try:
            root = ticker.upper()
            y, m, d = expiry.split('-')
            y = y[-2:]
            m = m.zfill(2)
            d = d.zfill(2)
            cp = 'C' if opt_type.lower().startswith('c') else 'P'
            strike_int = int(float(strike) * 1000)
            occ = f"{root}{y}{m}{d}{cp}{strike_int:08d}"
            url = f"https://api.polygon.io/v3/reference/options/contracts/{occ}"
            params = {"apiKey": self.polygon_key}
            response = requests.get(url, params=params)
            data = response.json()
            greeks = data.get('results', {}).get('greeks', {})
            return {
                'delta': greeks.get('delta'),
                'gamma': greeks.get('gamma'),
                'theta': greeks.get('theta'),
                'vega': greeks.get('vega')
            }
        except Exception as e:
            print(f"[POLYGON GREEKS ERROR] {ticker} {expiry} {strike} {opt_type}: {e}")
            return {'delta': None, 'gamma': None, 'theta': None, 'vega': None}
    def __init__(self):
        load_dotenv()
        self.polygon_key = os.environ.get("POLYGON_KEY")
        self.fred_key = os.environ.get("FRED_KEY")
        self.alpha_vantage_key = os.environ.get("ALPHA_VANTAGE")

    def get_prices(self, ticker):
        prices = {}
        # Polygon
        poly_price = None
        poly_vol = poly_avgvol = poly_chg = None
        if self.polygon_key:
            url = f"https://api.polygon.io/v2/aggs/ticker/{ticker}/prev"
            params = {"apiKey": self.polygon_key}
            try:
                response = requests.get(url, params=params)
                data = response.json()
                results = data.get("results", [])
                if results:
                    result = results[0]
                    poly_price = result['c']
                    poly_vol = result['v']
                    poly_avgvol = result.get('av', poly_vol)
                    poly_chg = round((result['c'] - result['o']) / result['o'] * 100, 2) if result['o'] else 0
                    prices['polygon'] = poly_price
            except Exception:
                poly_price = None
        # yfinance
        yf_price = None
        yf_vol = yf_avgvol = yf_chg = None
        try:
            yf_ticker = yf.Ticker(ticker)
            hist = yf_ticker.history(period="2d")
            if not hist.empty:
                last = hist.iloc[-1]
                prev = hist.iloc[-2] if len(hist) > 1 else last
                yf_price = last['Close']
                yf_vol = last['Volume']
                yf_avgvol = hist['Volume'].mean()
                yf_chg = round((last['Close'] - prev['Close']) / prev['Close'] * 100, 2) if prev['Close'] else 0
                prices['yfinance'] = yf_price
        except Exception:
            yf_price = None
        # Alpha Vantage
        av_price = None
        av_vol = None
        if self.alpha_vantage_key:
            av_url = f'https://www.alphavantage.co/query'
            av_params = {
                'function': 'TIME_SERIES_DAILY_ADJUSTED',
                'symbol': ticker,
                'apikey': self.alpha_vantage_key
            }
            try:
                av_resp = requests.get(av_url, params=av_params, timeout=10)
                av_data = av_resp.json()
                ts = av_data.get('Time Series (Daily)', {})
                if ts:
                    latest = sorted(ts.keys())[-1]
                    av_price = float(ts[latest]['4. close'])
                    av_vol = int(ts[latest]['6. volume'])
                    prices['alphavantage'] = av_price
            except Exception:
                av_price = None
        # Debug print
        print(f"[DEBUG] {ticker} prices: yfinance={yf_price}, polygon={poly_price}, alphavantage={av_price}")
        # Selection logic: prefer yfinance, then polygon, then alphavantage, else median if all present
        selected_price = None
        if yf_price is not None:
            selected_price = yf_price
            chg = yf_chg
            vol = yf_vol
            avgvol = yf_avgvol
        elif poly_price is not None:
            selected_price = poly_price
            chg = poly_chg
            vol = poly_vol
            avgvol = poly_avgvol
        elif av_price is not None:
            selected_price = av_price
            chg = 0
            vol = av_vol
            avgvol = av_vol
        else:
            # fallback: median of all available
            valid_prices = [p for p in prices.values() if p is not None]
            if valid_prices:
                valid_prices.sort()
                mid = len(valid_prices) // 2
                if len(valid_prices) % 2 == 1:
                    selected_price = valid_prices[mid]
                else:
                    selected_price = (valid_prices[mid-1] + valid_prices[mid]) / 2
                chg = 0
                vol = None
                avgvol = None
            else:
                return {'Ticker': ticker, 'Price': None, 'ChgPct': None, 'Volume': None, 'AvgVol': None}
        return {
            'Ticker': ticker,
            'Price': selected_price,
            'ChgPct': chg,
            'Volume': vol,
            'AvgVol': avgvol,
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
        required_cols = ['strike', 'type', 'impliedVolatility', 'expiry']
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
        # Robustify av_options after try/except, before any use
        if av_options is not None:
            if not isinstance(av_options, pd.DataFrame) or av_options.empty:
                av_options = pd.DataFrame(columns=required_cols)
            if len(av_options.columns) == 0:
                av_options = pd.DataFrame(columns=required_cols)
            if 'contractType' in av_options.columns:
                av_options = av_options.rename(columns={'contractType': 'type'})
            if 'type' not in av_options.columns:
                if 'contractSymbol' in av_options.columns:
                    def infer_type(symbol):
                        if isinstance(symbol, str) and len(symbol) > 0:
                            if symbol[-9] == 'C':
                                return 'call'
                            elif symbol[-9] == 'P':
                                return 'put'
                        return None
                    av_options['type'] = av_options['contractSymbol'].apply(infer_type)
                else:
                    av_options['type'] = None
            for col in required_cols:
                if col not in av_options.columns:
                    av_options[col] = None

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
        # Robustify yf_options after try/except, before any use
        required_cols = ['strike', 'type', 'impliedVolatility', 'expiry']
        if yf_options is not None:
            if not isinstance(yf_options, pd.DataFrame) or yf_options.empty:
                yf_options = pd.DataFrame(columns=required_cols)
            if len(yf_options.columns) == 0:
                yf_options = pd.DataFrame(columns=required_cols)
            if 'contractType' in yf_options.columns:
                yf_options = yf_options.rename(columns={'contractType': 'type'})
            if 'type' not in yf_options.columns:
                if 'contractSymbol' in yf_options.columns:
                    def infer_type(symbol):
                        if isinstance(symbol, str) and len(symbol) > 0:
                            if symbol[-9] == 'C':
                                return 'call'
                            elif symbol[-9] == 'P':
                                return 'put'
                        return None
                    yf_options['type'] = yf_options['contractSymbol'].apply(infer_type)
                else:
                    yf_options['type'] = None
            for col in required_cols:
                if col not in yf_options.columns:
                    yf_options[col] = None

        # No need to robustify yf_options again here; already done above
        # Cross-check and merge
        if av_options is not None and not av_options.empty:
            if yf_options is not None:
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
        elif yf_options is not None:
            return yf_options[required_cols]
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
