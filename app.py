from flask import Flask, render_template_string
import requests
import pandas as pd
import plotly.graph_objs as go
import yfinance as yf
import pandas_ta as ta # टेक्निकल इंडिकेटर्स के लिए
from datetime import datetime

app = Flask(__name__)

SYMBOLS = ["NIFTY50", "BANKNIFTY", "BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT"]
TRADE_LOG = [] 

def get_data(symbol):
    if symbol in ["NIFTY50", "BANKNIFTY"]:
        tk = "^NSEI" if symbol == "NIFTY50" else "^NSEBANK"
        try:
            # पिछले 2 दिनों का डेटा ताकि Open/Close दोनों मिल सकें
            data = yf.download(tk, period="2d", interval="15m", progress=False)
            if not data.empty:
                df = data[['Open', 'High', 'Low', 'Close']].copy()
                df.columns = ["open", "high", "low", "close"]
                # टेक्निकल इंडिकेटर्स जोड़ना
                df['rsi'] = ta.rsi(df['close'], length=14)
                return df
        except: pass
    else:
        try:
            url = f"https://binance.com{symbol}&interval=15m&limit=100"
            res = requests.get(url, timeout=5)
            df = pd.DataFrame(res.json(), columns=['t','open','high','low','close','v','ct','q','n','tb','tq','i'])
            df = df[['open','high','low','close']].apply(pd.to_numeric)
            df['rsi'] = ta.rsi(df['close'], length=14)
            return df
        except: pass
    return pd.DataFrame()

def strategy_logic(df):
    if df.empty or len(df) < 20: return "WAIT", "white"
    last = df.iloc[-1]
    ema9 = df['close'].ewm(span=9).mean().iloc[-1]
    # RSI + EMA कन्फर्मेशन
    if last['close'] > ema9 and last['rsi'] > 50: return "BUY", "#00ff00"
    if last['close'] < ema9 and last['rsi'] < 40: return "SELL", "#ff4444"
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
            <tr class='symbol-row'>
                <td style='padding:12px;'><b>{sym}</b></td>
                <td>{last['open']:,.2f}</td>
                <td style='color:#00d1ff;'>{last['close']:,.2f}</td>
                <td>{prev_close:,.2f}</td>
                <td style='color:{col}; font-weight:bold;'>{sig}</td>
            </tr>
            """
    
    # UI Layout with Search and Multi-Timeframe buttons
    return f"""
    <html>
    <head>
        <meta http-equiv="refresh" content="60">
        <style>
            body {{ background:#0e1117; color:white; font-family:sans-serif; padding:20px; }}
            .card {{ background:#1a1c24; border-radius:12px; padding:20px; border:1px solid #333; }}
            input {{ background:#2d2f3b; border:1px solid #444; color:white; padding:8px; border-radius:5px; width:100%; margin-bottom:10px; }}
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
            <!-- Watchlist with Search -->
            <div class="card" style="flex:1; min-width:350px;">
                <h3>Live Watchlist</h3>
                <input type="text" id="searchInput" onkeyup="filterWatchlist()" placeholder="Search Symbol (e.g. NIFTY)...">
                <table style='width:100%; border-collapse: collapse;'>
                    <tr><th>SYMBOL</th><th>OPEN</th><th>LTP</th><th>PREV CLOSE</th><th>SIGNAL</th></tr>
                    {rows}
                </table>
            </div>

            <!-- Advanced Analysis Chart -->
            <div class="card" style="flex:2; min-width:500px;">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <h3 style="margin:0;">Market Analysis (BTC/USDT)</h3>
                    <div>
                        <button style="background:#333; color:white; border:none; padding:5px 10px; border-radius:3px; cursor:pointer;">5m</button>
                        <button style="background:#00d1ff; color:black; border:none; padding:5px 10px; border-radius:3px; cursor:pointer;">15m</button>
                        <button style="background:#333; color:white; border:none; padding:5px 10px; border-radius:3px; cursor:pointer;">1h</button>
                    </div>
                </div>
                <div style="margin-top:15px;">
                    <!-- यहाँ आपका चार्ट आएगा -->
                    <div style="height:350px; background:#111; display:flex; align-items:center; justify-content:center; color:#555; border:1px dashed #444;">
                        Chart Loading with RSI & EMA...
                    </div>
                </div>
            </div>
        </div>

        <!-- News & Sentiment Mockup -->
        <div class="card" style="margin-top:20px;">
            <h3 style="color:#f39c12;">🔥 Live Sentiment & News</h3>
            <p style="font-size:14px; color:#bbb;">• US Inflation data expected today - Market Volatility high.</p>
            <p style="font-size:14px; color:#bbb;">• Nifty showing strong support at 23,800 levels.</p>
        </div>
    </body>
    </html>
    """

if __name__ == "__main__":
    import os
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))










