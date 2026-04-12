from flask import Flask
import requests
import pandas as pd
import plotly.graph_objs as go
from datetime import datetime

app = Flask(__name__)

SYMBOLS = ["NIFTY50", "BANKNIFTY", "BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT"]

# असली यूजर जैसा दिखने के लिए एडवांस हेडर्स
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Connection": "keep-alive"
}

TRADE_LOG = [] 

# ================= ROBUST DATA FETCHING (Anti-Block) =================
def get_data(symbol):
    # 1. INDIAN MARKET (NIFTY/BANKNIFTY) - Using Query2 for stability
    if symbol in ["NIFTY50", "BANKNIFTY"]:
        tk = "^NSEI" if symbol == "NIFTY50" else "^NSEBANK"
        # URL को थोड़ा बदलकर ताकि ब्लॉक न हो
        url = f"https://yahoo.com{tk}?interval=15m&range=1d"
        try:
            res = requests.get(url, headers=HEADERS, timeout=15)
            json_data = res.json()
            indicators = json_data['chart']['result'][0]['indicators']['quote'][0]
            df = pd.DataFrame({
                "open": indicators['open'],
                "high": indicators['high'],
                "low": indicators['low'],
                "close": indicators['close']
            })
            return df.dropna().tail(100)
        except Exception as e:
            print(f"Index Error: {e}")
            return pd.DataFrame()

    # 2. CRYPTO MARKET (Direct & Alternative API)
    else:
        # Source 1: Binance Public API
        urls = [
            f"https://binance.com{symbol}&interval=15m&limit=100",
            f"https://binance.com{symbol}&interval=15m&limit=100"
        ]
        for url in urls:
            try:
                res = requests.get(url, headers=HEADERS, timeout=10)
                if res.status_code == 200:
                    df = pd.DataFrame(res.json(), columns=['t','open','high','low','close','v','ct','q','n','tb','tq','i'])
                    return df[['open','high','low','close']].apply(pd.to_numeric)
            except: continue
    return pd.DataFrame()

# ================= STRATEGY LOGIC =================
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
    
    sig, col = "WAIT", "white"
    if "ema200" in df.columns:
        if c > last["ema9"] > last["ema200"]: 
            sig, col = "BUY", "#00ff00"
            if not TRADE_LOG or TRADE_LOG[-1]['sym'] != symbol:
                TRADE_LOG.append({'time': datetime.now().strftime("%H:%M"), 'sym': symbol, 'signal': 'BUY', 'price': c, 'pnl': 0.0, 'color': '#00ff00'})
        elif c < last["ema9"] < last["ema200"]: 
            sig, col = "SELL", "#ff4444"
            if not TRADE_LOG or TRADE_LOG[-1]['sym'] != symbol:
                TRADE_LOG.append({'time': datetime.now().strftime("%H:%M"), 'sym': symbol, 'signal': 'SELL', 'price': c, 'pnl': 0.0, 'color': '#ff4444'})

    return sig, col, o, h, l, c

# ================= CHART =================
def get_chart():
    df = get_data("BTCUSDT")
    if df.empty: return "<div style='color:#f39c12; padding:20px;'>Re-establishing connection...</div>"
    fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['open'], high=df['high'], low=df['low'], close=df['close'])])
    fig.update_layout(template="plotly_dark", height=400, margin=dict(l=0,r=0,t=0,b=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
    return fig.to_html(full_html=False)

# ================= UI =================
@app.route("/")
def dashboard():
    rows = ""
    for sym in SYMBOLS:
        sig, col, o, h, l, c = strategy(sym)
        price_txt = f"{c:,.2f}" if c > 0 else "---"
        rows += f"<tr style='border-bottom:1px solid #333;'><td style='padding:12px;'>{sym}</td><td style='color:#00d1ff;'>{price_txt}</td><td style='color:{col}; font-weight:bold;'>{sig}</td></tr>"

    j_rows = "".join([f"<tr style='border-bottom:1px solid #444;'><td style='padding:10px;'>{t['time']}</td><td>{t['sym']}</td><td style='color:{t['color']}'>{t['signal']}</td><td>{t['price']:.2f}</td><td>{t['pnl']:.2f}</td></tr>" for t in reversed(TRADE_LOG[-5:])])

    return f"""
    <html>
    <head><meta http-equiv="refresh" content="60"></head>
    <body style="background:#0e1117; color:white; font-family:sans-serif; padding:20px; margin:0;">
        <h2 style='text-align:center; color:#00d1ff; letter-spacing:1px;'>🚀 PRO TRADING DASHBOARD</h2>
        <div style="display:flex; gap:20px; flex-wrap:wrap; justify-content:center;">
            <div style="flex:1; min-width:320px; background:#1a1c24; padding:20px; border-radius:12px; border:1px solid #333;">
                <h3 style='margin-top:0; border-bottom:1px solid #444; padding-bottom:10px;'>Watchlist</h3>
                <table style='width:100%; border-collapse: collapse;'>{rows}</table>
            </div>
            <div style="flex:2; min-width:500px; background:#1a1c24; padding:20px; border-radius:12px; border:1px solid #333;">
                <h3 style='margin-top:0; border-bottom:1px solid #444; padding-bottom:10px;'>Market Analysis (BTC/USDT)</h3>
                {get_chart()}
            </div>
        </div>
        <div style="margin-top:20px; background:#1a1c24; padding:25px; border-radius:12px; border:1px solid #333;">
            <h3 style='margin-top:0; border-bottom:1px solid #444; padding-bottom:10px;'>📜 Live Trading Journal</h3>
            <table style='width:100%; border-collapse: collapse; text-align:left;'>
                <tr style='color:#888; border-bottom:2px solid #333;'><th>TIME</th><th>SYMBOL</th><th>ACTION</th><th>PRICE</th><th>P&L</th></tr>
                {j_rows if j_rows else "<tr><td colspan='5' style='text-align:center; padding:30px; color:#555;'>No signals yet. Watching markets...</td></tr>"}
            </table>
        </div>
    </body>
    </html>
    """

if __name__ == "__main__":
    import os
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))








