# polygon_ws.py
# Background WebSocket client for Polygon.io real-time options data
import websocket
import threading
import json
import os
import queue

POLYGON_KEY = "uz85txFQaRLRhVMNEwUfZr4wzIVcXgf0"
# ENSURE ONLY DELAYED ENDPOINT IS USED
WS_URL = "wss://delayed.polygon.io/options"

# Thread-safe queue to store latest messages for Streamlit
ws_queue = queue.Queue(maxsize=100)




# Helper to build Polygon option symbol for ATM call for nearest expiry
import yfinance as yf
from datetime import datetime


# Subscribe to ATM call and underlying for each ticker (delayed)

# Restore original logic: subscribe to ATM call and underlying for each ticker
def build_option_symbols(ticker):
    symbols = []
    try:
        ytkr = yf.Ticker(ticker)
        expiries = ytkr.options
        if not expiries:
            return []
        expiry = expiries[0]  # nearest expiry
        opt_chain = ytkr.option_chain(expiry)
        calls = opt_chain.calls
        underlying_price = ytkr.history(period="1d")['Close'].iloc[-1]
        if not calls.empty:
            atm_strike = min(calls['strike'], key=lambda x: abs(x - underlying_price))
            # Polygon format: O:{underlying}{yymmdd}{C/P}{strike*1000:08d}
            dt = datetime.strptime(expiry, "%Y-%m-%d")
            yymmdd = dt.strftime("%y%m%d")
            strike_int = int(round(atm_strike * 1000))
            option_symbol = f"T.O:{ticker.upper()}{yymmdd}C{strike_int:08d}"
            symbols.append(option_symbol)
        # Also subscribe to underlying trades (T.{TICKER})
        underlying_symbol = f"T.{ticker.upper()}"
        symbols.append(underlying_symbol)
    except Exception as e:
        print(f"[WS SYMBOL ERROR] {ticker}: {e}")
    return symbols


def on_message(ws, message):
    print("[WS MESSAGE]", message)  # Debug: print all incoming messages
    try:
        data = json.loads(message)
        if ws_queue.full():
            ws_queue.get()
        ws_queue.put(data)
    except Exception as e:
        print(f"[WS ERROR] {e}")

def on_open(ws, ticker):
    ws.send(json.dumps({"action": "auth", "params": POLYGON_KEY}))
    # Subscribe only to the selected ticker
    for symbol in build_option_symbols(ticker):
        print(f"[WS SUBSCRIBE] {symbol}")
        ws.send(json.dumps({"action": "subscribe", "params": symbol}))
    print(f"[WS] Subscribed to: {ticker}")


# Global reference to the current WebSocket and thread
current_ws = None
current_thread = None
ws_lock = threading.Lock()

def run_ws(ticker):
    def _on_open(ws):
        on_open(ws, ticker)
    global current_ws
    ws = websocket.WebSocketApp(WS_URL, on_open=_on_open, on_message=on_message)
    with ws_lock:
        current_ws = ws
    ws.run_forever()

# Helper to close the current WebSocket connection
def close_ws():
    global current_ws, current_thread
    with ws_lock:
        if current_ws is not None:
            try:
                current_ws.close()
            except Exception as e:
                print(f"[WS CLOSE ERROR] {e}")
            current_ws = None
        if current_thread is not None:
            try:
                # Wait for thread to finish (with timeout)
                current_thread.join(timeout=2)
            except Exception as e:
                print(f"[WS THREAD JOIN ERROR] {e}")
            current_thread = None

# Start WebSocket in a background thread for a specific ticker
def start_ws_thread(ticker):
    global current_thread
    close_ws()  # Always close any previous WebSocket before starting a new one
    thread = threading.Thread(target=run_ws, args=(ticker,), daemon=True)
    with ws_lock:
        current_thread = thread
    thread.start()

# Helper for Streamlit to get latest messages
def get_latest_ws_data():
    items = []
    while not ws_queue.empty():
        items.append(ws_queue.get())
    return items
