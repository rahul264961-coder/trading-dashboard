from flask import Flask
import requests
import pandas as pd
import plotly.graph_objs as go
from datetime import datetime

app = Flask(__name__)

# SYMBOLS: Indian Indices + Crypto
SYMBOLS = ["NIFTY50", "BANKNIFTY", "BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT"]

# असली ब्राउज़र जैसा दिखने के लिए हेडर्स (ताकि ब्लॉक न हो)
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}

TRADE_LOG = [] 

# ================= FIXED DATA FETCHING (Corrected URLs) =================
def get_data(symbol, interval="15m"):
    # 1. Indian Market (Yahoo Finance Fixed URL)
    if symbol in ["NIFTY50", "BANKNIFTY"]:
        ticker = "^NSEI" if symbol == "NIFTY50" else "^NSEBANK"
        url = f"https://yahoo.com{ticker}?interval=15m&range=1d"
        try:
            res = requests.get(url, headers=HEADERS, timeout=10)
            json_data = res.json()
            result = json_data['chart']['result'][0]
            df = pd.DataFrame({
                "open": result['indicators']['quote'][0]['open'],
                "high": result['indicators']['quote'][0]['high'],
                "low": result['indicators']['quote'][0]['low'],
                "close": result['indicators']['quote'][0]['close']
            })
            return df.dropna().tail(100)
        except Exception as e:
            print(f"Error Indian Data ({symbol}): {e}")
            return pd.DataFrame()

    # 2. Crypto Market (Binance Fixed URL)
    else:
        url = f"https://binance.com{symbol}&interval={interval}&limit=100"
        try:
            res = requests.get(url, headers=HEADERS, timeout=10)
            if res.status_code == 200:
                data = res.json()
                df = pd.DataFrame(data, columns=['time','open','high','low','close','v','ct','q','n','t','tb','i'])
                df = df[['open','high','low','close']].apply(pd.to_numeric)
                return df
        except Exception as e:
            print(f"Error Crypto Data ({symbol}): {e}")
            return pd.DataFrame()
    
    return pd.DataFrame()

# ================= EMA & STRATEGY (Same Logic) =================
def apply_ema(df):
    if df.empty or len(df) < 20: return df
    df["ema9"] = df["close"].ewm(span=9).mean()
    df["ema200"] = df["close"].ewm(span=200).mean()
    return df

def strategy(symbol):
    df = get_data(symbol)
    if df.empty: return "OFFLINE", "orange", 0,0,0,0
    
    df = apply_ema(df)
    last = df.iloc[-1]
    o, h, l, c = last["open"], last["high"], last["low"], last["close"]
    
    signal, color = "WAIT", "white"
    if "ema9" in df.columns and "ema200" in df.columns:
        if c > last["ema9"] > last["ema200"]: 
            signal, color = "BUY", "#00ff00"
            if not TRADE_LOG or TRADE_LOG[-1]['sym'] != symbol:
                TRADE_LOG.append({'time': datetime.now().strftime("%H:%M"), 'sym': symbol, 'signal': 'BUY', 'price': c, 'pnl': 0.0, 'color': '#00ff00'})
        elif c < last["ema9"] < last["ema200"]: 
            signal, color = "SELL", "#ff4444"
            if not TRADE_LOG or TRADE_LOG[-1]['sym'] != symbol:
                TRADE_LOG.append({'time': datetime.now().strftime("%H:%M"), 'sym': symbol, 'signal': 'SELL', 'price': c, 'pnl': 0.0, 'color': '#ff4444'})

    return signal, color, o, h, l, c

# ================= CHART (As Requested: No Changes to Options) =================
def get_chart():
    df = get_data("BTCUSDT")
    if df.empty: return "<div style='color:orange; padding:20px;'>Connecting to Market Data...</div>"
    
    fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['open'], high=df['high'], low=df['low'], close=df['close'])])
    fig.update_layout(template="plotly_dark", height=400, margin=dict(l=0,r=0,t=0,b=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
    return fig.to_html(full_html=False)

# ================= UI =================
@app.route("/")
def dashboard():
    rows = ""
    for sym in SYMBOLS:
        sig, col, o, h, l, c = strategy(sym)
        price_display = f"{c:,.2f}" if c > 0 else "---"
        rows += f"<tr style='border-bottom:1px solid #333;'><td style='padding:12px;'>{sym}</td><td style='color:#00d1ff;'>{price_display}</td><td style='color:{col}; font-weight:bold;'>{sig}</td></tr>"

    journal_rows = ""
    for trade in reversed(TRADE_LOG[-5:]):
        journal_rows += f"<tr style='border-bottom: 1px solid #444;'><td style='padding:10px;'>{trade['time']}</td><td>{trade['sym']}</td><td style='color:{trade['color']}'>{trade['signal']}</td><td>{trade['price']:.2f}</td><td>{trade['pnl']:.2f}</td></tr>"

    return f"""
    <html>
    <head><meta http-equiv="refresh" content="30"></head>
    <body style="background:#0e1117; color:white; font-family:sans-serif; padding:20px; margin:0;">
    <h2 style='text-align:center; color:#00d1ff;'>🚀 PRO TRADING HUB (FIXED)</h2>
    <div style="display:flex; flex-wrap:wrap; gap:20px; justify-content:center;">
        <div style="flex:1; min-width:300px; max-width:350px; background:#1a1c24; border-radius:12px; padding:20px; border:1px solid #333;">
            <h3 style='margin-top:0;'>Watchlist</h3>
            <table style='width:100%; border-collapse: collapse;'>{rows}</table>
        </div>
        <div style="flex:2; min-width:500px; background:#1a1c24; border-radius:12px; padding:20px; border:1px solid #333;">
            <h3 style='margin-top:0;'>Live Chart</h3> {get_chart()}
        </div>
    </div>
    <div style="margin-top:20px; background:#1a1c24; border-radius:12px; padding:20px; border:1px solid #333;">
        <h3 style='margin-top:0;'>📜 Live Trading Journal</h3>
        <table style='width:100%; border-collapse: collapse; text-align:left;'>
            <tr style='color:#888; border-bottom:2px solid #333;'><th>TIME</th><th>SYMBOL</th><th>ACTION</th><th>PRICE</th><th>P&L</th></tr>
            {journal_rows if journal_rows else "<tr><td colspan='5' style='text-align:center; padding:30px; color:#555;'>Watching markets...</td></tr>"}
        </table>
    </div>
    </body>
    </html>
    """

if __name__ == "__main__":
    import os
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))




