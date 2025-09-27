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

class OptionAProvider(DataProvider):
    def __init__(self, price_csv='prices.csv', greeks_csv='greeks.csv', sentiment_csv='sentiment.csv'):
        self.price_csv = price_csv
        self.greeks_csv = greeks_csv
        self.sentiment_csv = sentiment_csv
    def get_prices(self, ticker):
        df = pd.read_csv(self.price_csv)
        return df[df['Ticker'] == ticker].iloc[-1]
    def get_historicals(self, ticker):
        df = pd.read_csv(self.price_csv)
        return df[df['Ticker'] == ticker]['Close'].tail(30)
    def get_option_chain(self, ticker):
        df = pd.read_csv(self.greeks_csv)
        return df[df['Ticker'] == ticker]
    def get_sentiment(self):
        df = pd.read_csv(self.sentiment_csv)
        return df.iloc[-1]
