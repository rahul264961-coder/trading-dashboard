from flask import Flask
import requests
import pandas as pd
import plotly.graph_objs as go
from datetime import datetime
import time

app = Flask(__name__)

# SYMBOLS
SYMBOLS = ["NIFTY50", "BANKNIFTY", "BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT"]

# असली ब्राउज़र जैसा दिखने के लिए हेडर्स
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Referer": "https://google.com"
}

TRADE_LOG = [] 

def get_data(symbol):
    # --- INDIAN MARKET (Using a more stable endpoint) ---
    if symbol in ["NIFTY50", "BANKNIFTY"]:
        tk = "^NSEI" if symbol == "NIFTY50" else "^NSEBANK"
        url = f"https://yahoo.com{tk}?interval=15m&range=1d"
        try:
            res = requests.get(url, headers=HEADERS, timeout=10)
            data = res.json()['chart']['result'][0]['indicators']['quote'][0]
            df = pd.DataFrame({
                "open": data['open'], "high": data['high'], 
                "low": data['low'], "close": data['close']
            })
            return df.dropna().tail(100)
        except: return pd.DataFrame()

    # --- CRYPTO (Using Public API fallback) ---
    else:
        # Binance API के 2 अलग-अलग URL ताकि ब्लॉक न हो
        urls = [
            f"https://binance.com{symbol}&interval=15m&limit=100",
            f"https://binance.com{symbol}&interval=15m&limit=100"
        ]
        for url in urls:
            try:
                res = requests.get(url, headers=HEADERS, timeout=5)
                if res.status_code == 200:
                    d = res.json()
                    df = pd.DataFrame(d, columns=['t','open','high','low','close','v','ct','q','n','tb','tq','i'])
                    return df[['open','high','low','close']].apply(pd.to_numeric)
            except: continue
        return pd.DataFrame()

def apply_ema(df):
    if df.empty or len(df) < 20: return df
    df["ema9"] = df["close"].ewm(span=9).mean()
    df["ema200"] = df["close"].ewm(span=200).mean()
    return df

def strategy(symbol):
    df = get_data(symbol)
    if df.empty: return "RECONNECTING", "#f39c12", 0,0,0,0
    
    df = apply_ema(df)
    last = df.iloc[-1]
    o, h, l, c = last["open"], last["high"], last["low"], last["close"]
    
    # Signal Logic
    sig, col = "WAIT", "white"
    if c > last.get("ema9", 0) > last.get("ema200", 0): 
        sig, col = "BUY", "#00ff00"
        if not TRADE_LOG or TRADE_LOG[-1]['sym'] != symbol:
            TRADE_LOG.append({'time': datetime.now().strftime("%H:%M"), 'sym': symbol, 'signal': 'BUY', 'price': c, 'pnl': 0.0, 'color': '#00ff00'})
    elif c < last.get("ema9", 0) < last.get("ema200", 0): 
        sig, col = "SELL", "#ff4444"
        if not TRADE_LOG or TRADE_LOG[-1]['sym'] != symbol:
            TRADE_LOG.append({'time': datetime.now().strftime("%H:%M"), 'sym': symbol, 'signal': 'SELL', 'price': c, 'pnl': 0.0, 'color': '#ff4444'})

    return sig, col, o, h, l, c

@app.route("/")
def dashboard():
    rows = ""
    for sym in SYMBOLS:
        sig, col, o, h, l, c = strategy(sym)
        rows += f"<tr style='border-bottom:1px solid #333;'><td style='padding:12px;'>{sym}</td><td style='color:#00d1ff;'>{c:,.2f}</td><td style='color:{col}; font-weight:bold;'>{sig}</td></tr>"

    # Journal logic
    journal_rows = ""
    for trade in reversed(TRADE_LOG[-5:]):
        journal_rows += f"<tr style='border-bottom:1px solid #444;'><td style='padding:8px;'>{trade['time']}</td><td>{trade['sym']}</td><td style='color:{trade['color']}'>{trade['signal']}</td><td>{trade['price']:.2f}</td><td>{trade['pnl']:.2f}</td></tr>"

    return f"""
    <html>
    <head><meta http-equiv="refresh" content="20"></head>
    <body style="background:#0e1117; color:white; font-family:sans-serif; padding:20px;">
        <h2 style='text-align:center;'>🚀 PRO TRADING HUB (FIXED CONNECTION)</h2>
        <div style="display:flex; gap:20px; flex-wrap:wrap;">
            <div style="flex:1; background:#1a1c24; padding:20px; border-radius:10px; border:1px solid #333;">
                <h3>Watchlist</h3>
                <table style='width:100%; border-collapse: collapse;'>{rows}</table>
            </div>
            <div style="flex:2; background:#1a1c24; padding:20px; border-radius:10px; border:1px solid #333;">
                <h3>Live Trading Journal</h3>
                <table style='width:100%; border-collapse: collapse; text-align:left;'>
                    <tr style='color:#888;'><th>TIME</th><th>SYMBOL</th><th>ACTION</th><th>PRICE</th><th>P&L</th></tr>
                    {journal_rows if journal_rows else "<tr><td colspan='5' style='text-align:center; padding:20px;'>Searching for opportunities...</td></tr>"}
                </table>
            </div>
        </div>
    </body>
    </html>
    """

if __name__ == "__main__":
    import os
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))



