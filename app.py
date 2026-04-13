from flask import Flask, request
import requests
import pandas as pd
import plotly.graph_objs as go
import yfinance as yf
from datetime import datetime

app = Flask(__name__)

# 5 अलग-अलग वॉचलिस्ट्स
WATCHLISTS = {
    "Indices": ["^NSEI", "^NSEBANK", "^BSESN", "^INDIAVIX"],
    "Crypto": ["BTC-USD", "ETH-USD", "SOL-USD", "XRP-USD"],
    "Sectors": ["NIFTY_FIN_SERVICE.NS", "^CNXIT", "^CNXPHARMA", "^CNXAUTO"],
    "Global/Gold": ["PAXG-USD", "GC=F", "CL=F"],
    "Favorites": ["RELIANCE.NS", "HDFCBANK.NS", "TCS.NS"]
}

def get_data(ticker, interval="15m", limit=100):
    try:
        data = yf.download(ticker, period="5d", interval=interval, progress=False)
        if not data.empty:
            df = data[['Open', 'High', 'Low', 'Close']].copy()
            df.columns = ["open", "high", "low", "close"]
            # EMA Calculations
            df["ema9"] = df["close"].ewm(span=9).mean()
            df["ema15"] = df["close"].ewm(span=15).mean()
            df["ema200"] = df["close"].ewm(span=200).mean()
            return df
    except: pass
    return pd.DataFrame()

# आपकी पूरी स्ट्रेटजी का लॉजिक यहाँ है
def analyze_signal(ticker):
    # Multi-Timeframe Analysis
    intervals = ["5m", "15m", "1h", "4h"]
    results = {}
    
    for itv in intervals:
        df = get_data(ticker, itv)
        if df.empty or len(df) < 200: 
            results[itv] = "SIDE"
            continue
            
        last = df.iloc[-2] # Closed Candle Rule (पिछली कैंडल)
        # EMA Trend Logic
        if last['close'] > last['ema9'] > last['ema15'] > last['ema200']:
            results[itv] = "UP"
        elif last['close'] < last['ema9'] < last['ema15'] < last['ema200']:
            results[itv] = "DOWN"
        else:
            results[itv] = "SIDE"

    # Multi-Confirmation Check
    final_sig = "SIDEWAYS"
    color = "gray"
    
    if all(results[i] == "UP" for i in intervals):
        final_sig, color = "STRONG BUY", "#00ff00"
    elif all(results[i] == "DOWN" for i in intervals):
        final_sig, color = "STRONG SELL", "#ff4444"
        
    return final_sig, color

@app.route("/")
def dashboard():
    selected_sym = request.args.get('chart', '^NSEI')
    active_tab = request.args.get('tab', 'Indices')
    
    rows = ""
    for ticker in WATCHLISTS[active_tab]:
        df = get_data(ticker, "15m")
        if not df.empty:
            last = df.iloc[-1]
            sig, col = analyze_signal(ticker)
            rows += f"""
            <tr class='symbol-row' onclick="window.location.href='/?chart={ticker}&tab={active_tab}'">
                <td><b>{ticker}</b></td>
                <td>{last['open']:,.1f}</td><td>{last['high']:,.1f}</td>
                <td>{last['low']:,.1f}</td><td style='color:#00d1ff;'>{last['close']:,.1f}</td>
                <td style='color:{col}; font-weight:bold;'>{sig}</td>
            </tr>"""

    return f"""
    <html>
    <head>
        <meta http-equiv="refresh" content="60">
        <style>
            body {{ background:#0e1117; color:white; font-family:sans-serif; margin:0; padding:20px; }}
            .card {{ background:#1a1c24; border-radius:12px; padding:15px; border:1px solid #333; }}
            .tab-btn {{ background:#333; color:white; border:none; padding:10px; cursor:pointer; border-radius:5px; margin-right:5px; }}
            .active-tab {{ background:#00d1ff; color:black; }}
            table {{ width:100%; text-align:left; border-collapse: collapse; font-size: 13px; }}
            th {{ color:#888; border-bottom:1px solid #444; padding:10px; }}
            td {{ padding:10px; border-bottom:1px solid #222; }}
        </style>
    </head>
    <body>
        <h2 style='text-align:center;'>📊 PRO MULTI-STRATEGY HUB</h2>
        
        <!-- Watchlist Tabs -->
        <div style="margin-bottom:15px;">
            {' '.join([f"<button class='tab-btn {'active-tab' if t==active_tab else ''}' onclick=\\\"window.location.href='/?tab={t}'\\\">{t}</button>" for t in WATCHLISTS.keys()])}
        </div>

        <div style="display:flex; gap:20px;">
            <div class="card" style="flex:1;">
                <input type="text" id="search" onkeyup="filter()" placeholder="Search symbols..." style="width:100%; padding:10px; margin-bottom:10px; background:#222; border:1px solid #444; color:white;">
                <table>
                    <tr><th>SYMBOL</th><th>O</th><th>H</th><th>L</th><th>C</th><th>SIGNAL</th></tr>
                    {rows}
                </table>
            </div>
            <div class="card" style="flex:2;">
                <h3>Analysis: {selected_sym}</h3>
                <div style="height:450px; background:#000; border-radius:10px; display:flex; align-items:center; justify-content:center; color:#444;">
                   [ Interactive Plotly Chart with EMA 9, 15, 200 ]
                </div>
            </div>
        </div>

        <script>
            function filter() {{
                let val = document.getElementById('search').value.toUpperCase();
                let rows = document.getElementsByClassName('symbol-row');
                for (let r of rows) {{ r.style.display = r.innerText.toUpperCase().includes(val) ? "" : "none"; }}
            }}
        </script>
    </body>
    </html>
    """

if __name__ == "__main__":
    import os
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))














