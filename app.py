from flask import Flask
import requests
import pandas as pd
import plotly.graph_objs as go
import yfinance as yf
from datetime import datetime

app = Flask(__name__)

SYMBOLS = ["NIFTY50", "BANKNIFTY", "BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT"]
TRADE_LOG = [] 

# --- मैन्युअल RSI फंक्शन (बिना लाइब्रेरी के) ---
def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def get_data(symbol):
    if symbol in ["NIFTY50", "BANKNIFTY"]:
        tk = "^NSEI" if symbol == "NIFTY50" else "^NSEBANK"
        try:
            data = yf.download(tk, period="2d", interval="15m", progress=False)
            if not data.empty:
                df = data[['Open', 'High', 'Low', 'Close']].copy()
                df.columns = ["open", "high", "low", "close"]
                df['rsi'] = calculate_rsi(df['close'])
                return df
        except: pass
    else:
        try:
            url = f"https://binance.com{symbol}&interval=15m&limit=100"
            res = requests.get(url, timeout=5)
            df = pd.DataFrame(res.json(), columns=['t','open','high','low','close','v','ct','q','n','tb','tq','i'])
            df = df[['open','high','low','close']].apply(pd.to_numeric)
            df['rsi'] = calculate_rsi(df['close'])
            return df
        except: pass
    return pd.DataFrame()

def strategy_logic(df):
    if df.empty or len(df) < 20: return "WAIT", "white"
    last = df.iloc[-1]
    ema9 = df['close'].ewm(span=9).mean().iloc[-1]
    rsi_val = last['rsi']
    
    # Signal Logic
    if last['close'] > ema9 and rsi_val > 50: return "BUY", "#00ff00"
    if last['close'] < ema9 and rsi_val < 40: return "SELL", "#ff4444"
    return "WAIT", "white"

@app.route("/")
def dashboard():
    rows = ""
    for sym in SYMBOLS:
        df = get_data(sym)
        if not df.empty:
            last = df.iloc[-1]
            prev_close = df['close'].iloc[-2] if len(df) > 1 else last['open']
            sig, col = strategy_logic(df)
            rows += f"""
            <tr class='symbol-row' style='border-bottom:1px solid #333;'>
                <td style='padding:12px;'><b>{sym}</b></td>
                <td>{last['open']:,.2f}</td>
                <td style='color:#00d1ff;'>{last['close']:,.2f}</td>
                <td>{prev_close:,.2f}</td>
                <td style='color:{col}; font-weight:bold;'>{sig}</td>
            </tr>"""
    
    # UI वैसा ही है जैसा आपने पिछली बार पसंद किया था
    return f"""
    <html>
    <head>
        <meta http-equiv="refresh" content="60">
        <style>
            body {{ background:#0e1117; color:white; font-family:sans-serif; padding:20px; }}
            .card {{ background:#1a1c24; border-radius:12px; padding:20px; border:1px solid #333; margin-bottom:20px; }}
            input {{ background:#2d2f3b; border:1px solid #444; color:white; padding:10px; border-radius:5px; width:100%; margin-bottom:15px; }}
            th {{ text-align:left; color:#888; font-size:12px; padding-bottom:10px; }}
        </style>
        <script>
            function filterWatchlist() {{
                let input = document.getElementById('searchInput').value.toUpperCase();
                let rows = document.getElementsByClassName('symbol-row');
                for (let row of rows) {{
                    row.style.display = row.innerText.toUpperCase().includes(input) ? "" : "none";
                }}
            }}
        </script>
    </head>
    <body>
        <h2 style='text-align:center; color:#00d1ff;'>🚀 NEXT-GEN TRADING HUB PRO</h2>
        <div style="display:flex; gap:20px; flex-wrap:wrap;">
            <div class="card" style="flex:1; min-width:350px;">
                <h3>Live Watchlist</h3>
                <input type="text" id="searchInput" onkeyup="filterWatchlist()" placeholder="Search Symbol (e.g. NIFTY)...">
                <table style='width:100%; border-collapse: collapse;'>
                    <tr><th>SYMBOL</th><th>OPEN</th><th>LTP</th><th>PREV CLOSE</th><th>SIGNAL</th></tr>
                    {rows}
                </table>
            </div>
        </div>
    </body>
    </html>
    """

if __name__ == "__main__":
    import os
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))











