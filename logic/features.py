# features.py
# Indicator calculations: EMA, RSI, MACD, VolRatio, etc.
import pandas as pd

def ema(series, window):
    return series.ewm(span=window, adjust=False).mean()

def sma(series, window):
    return series.rolling(window=window).mean()

def rsi(series, window=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def macd(series, fast=12, slow=26, signal=9):
    ema_fast = ema(series, fast)
    ema_slow = ema(series, slow)
    macd_line = ema_fast - ema_slow
    signal_line = ema(macd_line, signal)
    return macd_line, signal_line

def vol_ratio(volume, avg_volume):
    return volume / avg_volume if avg_volume else 0
