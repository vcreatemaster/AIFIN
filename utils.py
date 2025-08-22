import yfinance as yf
import numpy as np
import requests
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(message)s')

def get_min_period(interval, max_window):
    candles_per_day = {
        "1m": 1440,
        "5m": 288,
        "15m": 96,
        "30m": 48,
        "1h": 24,
        "4h": 6,
        "1d": 1
    }
    if interval not in candles_per_day:
        raise ValueError(f"Unsupported interval: {interval}")
    needed_candles = max_window * 2
    days_needed = int(np.ceil(needed_candles / candles_per_day[interval]))
    return f"{days_needed}d"

def send_to_api(phone_number, message):
    url = "http://cs1.codetrox.com:5001/send-message"
    payload = {
        "session": "main",
        "to": "91" + str(phone_number),
        "text": message
    }
    try:
        response = requests.post(url, data=payload, timeout=10)
        if response.status_code == 200:
            logging.info(f"✅ Message sent to {phone_number}")
        else:
            logging.error(f"❌ Failed to send message: {response.status_code} | {response.text}")
    except Exception as e:
        logging.error(f"API error: {e}")

def fetch_data(ticker, interval, period, local_tz="Asia/Kolkata"):
    df = yf.download(ticker, interval=interval, period=period, progress=False, auto_adjust=False)
    if df.empty:
        raise ValueError("No data retrieved.")
    df.index = df.index.tz_convert(local_tz)
    return df