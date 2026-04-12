from flask import Flask
import requests
import pandas as pd
import plotly.graph_objs as go
from datetime import datetime

app = Flask(__name__)

SYMBOLS = ["NIFTY50", "BANKNIFTY", "BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT"]
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

TRADE_LOG = [] 

# ================= MULTI-API DATA ENGINE (Backup Support) =================
def get_data(symbol):
    # 1. INDIAN MARKET (NIFTY/BANKNIFTY)
    if symbol in ["NIFTY50", "BANKNIFTY"]:
        tk = "^NSEI" if symbol == "NIFTY50" else "^NSEBANK"
        url = f"https://yahoo.com{tk}?interval=15m&range=1d"
        try:
            res = requests.get(url, headers=HEADERS, timeout=10)
            data = res.json()['chart']['result'][0]
            df = pd.DataFrame({
                "open": data['indicators']['quote'][0]['open'],
                "high": data['indicators']['quote'][0]['high'],
                "low": data['indicators']['quote'][0]['low'],
                "close": data['indicators']['quote'][0]['close']
            })
            return df.dropna().tail(100)
        except: return pd.DataFrame()

    # 2. CRYPTO MARKET (Multi-Source: Binance -> Bybit -> Kucoin)
    else:
        # Source A: Binance
        try:
            url = f"https://binance.com{symbol}&interval=15m&limit=100"
            res = requests.get(url, headers=HEADERS, timeout=5)
            if res.status_code == 200:
                df = pd.DataFrame(res.json(), columns=['t','open','high','low','close','v','ct','q','n','tb','tq','i'])
                return df[['open','high','low','close']].apply(pd.to_numeric)
        except: pass

        # Source B: Bybit (Backup)
        try:
            url = f"https://bybit.com{symbol}&interval=15&limit=100"
            res = requests.get(url, headers=HEADERS, timeout=5)
            if res.status_code == 200:
                data = res.json()['result']['list']
                df = pd.DataFrame(data, columns=['t','open','high','low','close','v','turnover'])
                return df[['open','high','low','close']].apply(pd.to_numeric).iloc[::-1]
        except: pass

    return pd.DataFrame()

# ================= EMA & STRATEGY =================
def apply_ema(df):
    if df.empty or len(df) < 20: return df
    df["ema9"] = df["close"].ewm(span=9).mean()
    df["ema200"] = df["close"].ewm(span=200).mean()
    return df

def strategy(symbol):
    df = get_data(symbol)
    if df.empty: return "RECONNECTING", "orange", 0,0,0,0
    
    df = apply_ema(df)
    last = df.iloc[-1]
    o, h, l, c = last["open"], last["high"], last["low"], last["close"]
    
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

# ================= CHART =================
def get_chart():
    df = get_data("BTCUSDT")
    if df.empty: return "<div style='color:orange; padding:20px;'>Market Data Connecting...</div>"
    fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['open'], high=df['high'], low=df['low'], close=df['close'])])
    fig.update_layout(template="plotly_dark", height=400, margin=dict(l=0,r=0,t=0,b=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
    return fig.to_html(full_html=False)

# ================= UI =================
@app.route("/")
def dashboard():
    rows = ""
    for sym in SYMBOLS:
        sig, col, o, h, l, c = strategy(sym)
        rows += f"<tr style='border-bottom:1px solid #333;'><td style='padding:12px;'>{sym}</td><td style='color:#00d1ff;'>{c:,.2f}</td><td style='color:{col}; font-weight:bold;'>{sig}</td></tr>"

    j_rows = "".join([f"<tr style='border-bottom:1px solid #444;'><td style='padding:10px;'>{t['time']}</td><td>{t['sym']}</td><td style='color:{t['color']}'>{t['signal']}</td><td>{t['price']:.2f}</td><td>{t['pnl']:.2f}</td></tr>" for t in reversed(TRADE_LOG[-5:])])

    return f"""
    <html>
    <head><meta http-equiv="refresh" content="30"></head>
    <body style="background:#0e1117; color:white; font-family:sans-serif; padding:20px;">
        <h2 style='text-align:center; color:#00d1ff;'>🚀 NEXT-GEN TRADING HUB</h2>
        <div style="display:flex; gap:20px; flex-wrap:wrap;">
            <div style="flex:1; min-width:300px; background:#1a1c24; padding:20px; border-radius:10px; border:1px solid #444;">
                <h3>Watchlist</h3><table style='width:100%; border-collapse: collapse;'>{rows}</table>
            </div>
            <div style="flex:2; min-width:500px; background:#1a1c24; padding:20px; border-radius:10px; border:1px solid #444;">
                <h3>Market Analysis</h3>{get_chart()}
            </div>
        </div>
        <div style="margin-top:20px; background:#1a1c24; padding:20px; border-radius:10px; border:1px solid #444;">
            <h3>📜 Trading Journal</h3>
            <table style='width:100%; border-collapse: collapse; text-align:left;'>
                <tr style='color:#888; border-bottom:2px solid #333;'><th>TIME</th><th>SYMBOL</th><th>ACTION</th><th>PRICE</th><th>P&L</th></tr>
                {j_rows if j_rows else "<tr><td colspan='5' style='text-align:center; padding:20px;'>Scanning...</td></tr>"}
            </table>
        </div>
    </body>
    </html>
    """

if __name__ == "__main__":
    import os
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))







