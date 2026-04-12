from flask import Flask
import requests
import pandas as pd
import plotly.graph_objs as go
from datetime import datetime
import yfinance as yf  # इसे इस्तेमाल करने के लिए requirements.txt में yfinance जोड़ें

app = Flask(__name__)

SYMBOLS = ["NIFTY50", "BANKNIFTY", "BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT"]
TRADE_LOG = [] 

# ================= 🛡️ ULTRA ROBUST DATA ENGINE =================
def get_data(symbol):
    # --- 1. Indian Market (Using yfinance - Best for Render) ---
    if symbol in ["NIFTY50", "BANKNIFTY"]:
        tk = "^NSEI" if symbol == "NIFTY50" else "^NSEBANK"
        try:
            # yfinance ब्लॉक नहीं होता जल्दी
            data = yf.download(tk, period="1d", interval="15m", progress=False)
            if not data.empty:
                df = data[['Open', 'High', 'Low', 'Close']].copy()
                df.columns = ["open", "high", "low", "close"]
                return df
        except: pass

    # --- 2. Crypto Market (Binance + Backup Sources) ---
    else:
        # Source A: Binance Official
        try:
            url = f"https://binance.com{symbol}&interval=15m&limit=100"
            res = requests.get(url, timeout=10)
            if res.status_code == 200:
                df = pd.DataFrame(res.json(), columns=['t','open','high','low','close','v','ct','q','n','tb','tq','i'])
                return df[['open','high','low','close']].apply(pd.to_numeric)
        except: pass

        # Source B: yfinance for Crypto (Backup)
        try:
            crypto_tk = symbol.replace("USDT", "-USD")
            data = yf.download(crypto_tk, period="1d", interval="15m", progress=False)
            if not data.empty:
                df = data[['Open', 'High', 'Low', 'Close']].copy()
                df.columns = ["open", "high", "low", "close"]
                return df
        except: pass

    return pd.DataFrame()

# ================= 🧠 STRATEGY & LOGIC =================
def apply_ema(df):
    if df.empty or len(df) < 20: return df
    df["ema9"] = df["close"].ewm(span=9).mean()
    df["ema200"] = df["close"].ewm(span=200).mean()
    return df

def strategy(symbol):
    df = get_data(symbol)
    if df.empty: return "RE-CONNECTING", "orange", 0,0,0,0
    
    df = apply_ema(df)
    last = df.iloc[-1]
    o, h, l, c = last["open"], last["high"], last["low"], last["close"]
    
    sig, col = "WAIT", "white"
    if "ema200" in df.columns:
        if c > last["ema9"] > last["ema200"]: 
            sig, col = "BUY", "#00ff00"
            if not TRADE_LOG or TRADE_LOG[-1]['sym'] != symbol:
                TRADE_LOG.append({'time': datetime.now().strftime("%H:%M"), 'sym': symbol, 'signal': 'BUY', 'price': float(c), 'pnl': 0.0, 'color': '#00ff00'})
        elif c < last["ema9"] < last["ema200"]: 
            sig, col = "SELL", "#ff4444"
            if not TRADE_LOG or TRADE_LOG[-1]['sym'] != symbol:
                TRADE_LOG.append({'time': datetime.now().strftime("%H:%M"), 'sym': symbol, 'signal': 'SELL', 'price': float(c), 'pnl': 0.0, 'color': '#ff4444'})

    return sig, col, float(o), float(h), float(l), float(c)

# ================= 📊 DASHBOARD UI =================
def get_chart():
    df = get_data("BTCUSDT")
    if df.empty: return "<div style='color:#f39c12; padding:20px; text-align:center;'>Syncing with Global Market...</div>"
    fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['open'], high=df['high'], low=df['low'], close=df['close'])])
    fig.update_layout(template="plotly_dark", height=400, margin=dict(l=0,r=0,t=0,b=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
    return fig.to_html(full_html=False)

@app.route("/")
def dashboard():
    rows = ""
    for sym in SYMBOLS:
        sig, col, o, h, l, c = strategy(sym)
        p_txt = f"{c:,.2f}" if c > 0 else "Offline"
        rows += f"<tr style='border-bottom:1px solid #333;'><td style='padding:12px;'>{sym}</td><td style='color:#00d1ff;'>{p_txt}</td><td style='color:{col}; font-weight:bold;'>{sig}</td></tr>"

    j_rows = "".join([f"<tr style='border-bottom:1px solid #444;'><td style='padding:10px;'>{t['time']}</td><td>{t['sym']}</td><td style='color:{t['color']}'>{t['signal']}</td><td>{t['price']:.2f}</td><td>{t['pnl']:.2f}</td></tr>" for t in reversed(TRADE_LOG[-5:])])

    return f"""
    <html>
    <head><meta http-equiv="refresh" content="60"><title>Next-Gen Trading Hub</title></head>
    <body style="background:#0e1117; color:white; font-family:sans-serif; padding:20px; margin:0;">
        <h2 style='text-align:center; color:#00d1ff;'>🚀 NEXT-GEN TRADING HUB</h2>
        <div style="display:flex; gap:20px; flex-wrap:wrap; justify-content:center;">
            <div style="flex:1; min-width:320px; background:#1a1c24; padding:20px; border-radius:12px; border:1px solid #444;">
                <h3 style='margin-top:0;'>Live Watchlist</h3>
                <table style='width:100%; border-collapse: collapse;'>{rows}</table>
            </div>
            <div style="flex:2; min-width:500px; background:#1a1c24; padding:20px; border-radius:12px; border:1px solid #444;">
                <h3 style='margin-top:0;'>Market Analysis</h3>{get_chart()}
            </div>
        </div>
        <div style="margin-top:20px; background:#1a1c24; padding:25px; border-radius:12px; border:1px solid #444;">
            <h3 style='margin-top:0;'>📜 Live Trading Journal</h3>
            <table style='width:100%; border-collapse: collapse; text-align:left;'>
                <tr style='color:#888; border-bottom:2px solid #333;'><th>TIME</th><th>SYMBOL</th><th>ACTION</th><th>PRICE</th><th>P&L</th></tr>
                {j_rows if j_rows else "<tr><td colspan='5' style='text-align:center; padding:30px; color:#555;'>Looking for entries...</td></tr>"}
            </table>
        </div>
    </body>
    </html>
    """

if __name__ == "__main__":
    import os
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))









