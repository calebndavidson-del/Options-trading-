# Debug helper to print the first option contract with Greeks
import streamlit as st
import pandas as pd
import requests
import os

POLYGON_KEY = "uz85txFQaRLRhVMNEwUfZr4wzIVcXgf0"

ticker = "SPY"
url = f"https://api.polygon.io/v3/snapshot/options/{ticker.upper()}"
params = {"apiKey": POLYGON_KEY}
all_options = []
while url:
    response = requests.get(url, params=params)
    data = response.json()
    if 'results' in data and 'options' in data['results']:
        all_options.extend(data['results']['options'])
    url = data.get('next_url')
    params = {}

# Print the first contract with Greeks
for opt in all_options:
    if any(g in opt for g in ["delta", "gamma", "theta", "vega"]):
        print(opt)
        break
else:
    print("No Greeks found in any contract.")
