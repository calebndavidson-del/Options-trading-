import yfinance as yf
import pandas as pd
import datetime

def fetch_yfinance_options(ticker):
    ytkr = yf.Ticker(ticker)
    expiries = ytkr.options
    if not expiries:
        return pd.DataFrame()
    expiry = expiries[0]  # nearest expiry
    opt_chain = ytkr.option_chain(expiry)
    calls = opt_chain.calls.copy()
    calls['expiration_date'] = expiry
    # Add underlying price
    hist = ytkr.history(period="1d")
    underlying_price = hist['Close'].iloc[-1] if not hist.empty else None
    calls['underlying_price'] = underlying_price
    # Calculate days to expiry
    today = datetime.datetime.now().date()
    exp_date = datetime.datetime.strptime(expiry, "%Y-%m-%d").date()
    calls['days_to_expiry'] = (exp_date - today).days
    return calls
