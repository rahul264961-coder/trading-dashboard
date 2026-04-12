from flask import Flask
import requests
import pandas as pd
import plotly.graph_objs as go
from datetime import datetime

app = Flask(__name__)

# SYMBOLS: Indian Indices + Crypto
SYMBOLS = ["NIFTY50", "BANKNIFTY", "BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT"]
HEADERS = {"User-Agent": "Mozilla/5.0"}

# --- [ ADDED: Trade Log for Journal ] ---
TRADE_LOG = [] 

# ================= MULTI-API DATA FETCHING =================
def get_data(symbol, interval="15m"):
    interval_map = {"15m": "15", "1h": "60", "4h": "240"}
    
    # 1. Indian Market (Yahoo Finance)
    if symbol in ["NIFTY50", "BANKNIFTY"]:
        ticker = "^NSEI" if symbol == "NIFTY50" else "^NSEBANK"
        try:
            res = requests.get(f"https://yahoo.com{ticker}?interval=15m&range=5d", headers=HEADERS, timeout=5)
            data = res.json()['chart']['result'][0]
            df = pd.DataFrame({
                "open": data['indicators']['quote'][0]['open'],
                "high": data['indicators']['quote'][0]['high'],
                "low": data['indicators']['quote'][0]['low'],
                "close": data['indicators']['quote'][0]['close']
            })
            return df.dropna().tail(200)
        except: return pd.DataFrame()

    # 2. Backup APIs for Crypto (Binance -> Bybit -> Kucoin -> OKX)
    apis = [
        f"https://binance.com{symbol}&interval={interval}&limit=200",
        f"https://bybit.com{symbol}&interval={interval_map.get(interval,'15')}&limit=200",
        f"https://kucoin.com{symbol.replace('USDT','-USDT')}&type={interval}&limit=200"
    ]
    
    for url in apis:
        try:
            res = requests.get(url, headers=HEADERS, timeout=5)
            if res.status_code == 200:
                data = res.json()
                # Simple parsing logic for brevity
                if 'result' in data: d = data['result']['list'] # Bybit
                elif 'data' in data: d = data['data'] # Kucoin
                else: d = data # Binance
                
                df = pd.DataFrame(d).iloc[:, [1,2,3,4]].apply(pd.to_numeric)
                df.columns = ["open","high","low","close"]
                return df if not df.empty else pd.DataFrame()
        except: continue
    return pd.DataFrame()

# ================= EMA & STRATEGY (Same as yours) =================
def apply_ema(df):
    if df.empty: return df
    df["ema9"] = df["close"].ewm(span=9).mean()
    df["ema15"] = df["close"].ewm(span=15).mean()
    df["ema200"] = df["close"].ewm(span=200).mean()
    return df

def strategy(symbol):
    df = apply_ema(get_data(symbol))
    if df.empty: return "NO DATA", "red", 0,0,0,0
    
    last = df.iloc[-1]
    o, h, l, c = last["open"], last["high"], last["low"], last["close"]
    
    # Simple Signal Logic (Based on your EMA setup)
    signal, color = "-", "white"
    if c > last["ema9"] > last["ema200"]: 
        signal, color = "BUY", "green"
        # ऑटो-जर्नल में एंट्री (अगर नया सिग्नल है)
        if not TRADE_LOG or TRADE_LOG[-1]['sym'] != symbol:
            TRADE_LOG.append({'time': datetime.now().strftime("%H:%M:%S"), 'sym': symbol, 'signal': signal, 'price': c, 'pnl': 0, 'color': color})
    
    elif c < last["ema9"] < last["ema200"]: 
        signal, color = "SELL", "red"
        if not TRADE_LOG or TRADE_LOG[-1]['sym'] != symbol:
            TRADE_LOG.append({'time': datetime.now().strftime("%H:%M:%S"), 'sym': symbol, 'signal': signal, 'price': c, 'pnl': 0, 'color': color})

    return signal, color, o, h, l, c

# ================= CHART =================
def get_chart():
    df = apply_ema(get_data("BTCUSDT"))
    if df.empty: return "<h3 style='color:red;'>Waiting for Data...</h3>"
    fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['open'], high=df['high'], low=df['low'], close=df['close'])])
    fig.update_layout(template="plotly_dark", height=450, margin=dict(l=0,r=0,t=0,b=0))
    return fig.to_html(full_html=False)

# ================= UI =================
@app.route("/")
def dashboard():
    rows = ""
    for sym in SYMBOLS:
        sig, col, o, h, l, c = strategy(sym)
        rows += f"<tr style='border-bottom:1px solid #333;'><td style='padding:10px;'>{sym}</td><td>LTP: {c:.2f}</td><td style='color:{col}'>{sig}</td></tr>"

    journal_rows = ""
    for trade in reversed(TRADE_LOG[-10:]): # केवल आखिरी 10 ट्रेड्स
        journal_rows += f"<tr style='border-bottom: 1px solid #444;'><td style='padding:10px;'>{trade['time']}</td><td>{trade['sym']}</td><td style='color:{trade['color']}'>{trade['signal']}</td><td>{trade['price']:.2f}</td><td>{trade['pnl']:.2f}</td></tr>"

    return f"""
    <html>
    <head><meta http-equiv="refresh" content="15"></head>
    <body style="background:#0e1117; color:white; font-family:sans-serif; padding:20px;">
    <h2 style='text-align:center;'>🚀 PRO TRADING HUB (Multi-API)</h2>
    <div style="display:flex; gap:20px; margin-bottom: 20px;">
        <div style="width:30%; background:#1a1c24; border-radius:10px; padding:15px;">
            <h3>Watchlist</h3>
            <table style='width:100%; border-collapse: collapse;'>{rows}</table>
        </div>
        <div style="width:70%; background:#1a1c24; border-radius:10px; padding:15px;">
            <h3>Live Analysis</h3> {get_chart()}
        </div>
    </div>
    <div style="background:#1a1c24; border-radius:10px; padding:20px;">
        <h3>📜 Live Trading Journal</h3>
        <table style='width:100%; border-collapse: collapse;'>
            <tr style='color:#888; text-align:left;'><th>TIME</th><th>SYMBOL</th><th>ACTION</th><th>PRICE</th><th>P&L</th></tr>
            {journal_rows if journal_rows else "<tr><td colspan='5' style='text-align:center; padding:20px;'>No trades yet.</td></tr>"}
        </table>
    </div>
    </body>
    </html>
    """

if __name__ == "__main__":
    import os
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))


