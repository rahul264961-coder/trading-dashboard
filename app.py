from flask import Flask, request
import requests
import pandas as pd
import plotly.graph_objs as go
import yfinance as yf
from datetime import datetime

app = Flask(__name__)

# 1. आपके द्वारा मांगे गए सभी सिम्बल्स (Indian + Crypto + Gold)
SYMBOLS = {
    "NIFTY50": "^NSEI", "BANKNIFTY": "^NSEBANK", "FINNIFTY": "NIFTY_FIN_SERVICE.NS", 
    "SENSEX": "^BSESN", "MIDCAP_NIFTY": "NIFTY_MID_SELECT.NS", "INDIA_VIX": "^INDIAVIX",
    "GIFT_NIFTY": "GIFTY.NS", "BTCUSDT": "BTC-USD", "ETHUSDT": "ETH-USD", 
    "SOLUSDT": "SOL-USD", "XRPUSDT": "XRP-USD", "PAXG_GOLD": "PAXG-USD"
}

def get_data(ticker, interval="15m"):
    try:
        data = yf.download(ticker, period="5d", interval=interval, progress=False)
        if not data.empty:
            df = data[['Open', 'High', 'Low', 'Close']].copy()
            df.columns = ["open", "high", "low", "close"]
            # आपकी तीनों EMA जोड़ना
            df["ema9"] = df["close"].ewm(span=9).mean()
            df["ema15"] = df["close"].ewm(span=15).mean()
            df["ema200"] = df["close"].ewm(span=200).mean()
            return df
    except: pass
    return pd.DataFrame()

@app.route("/")
def dashboard():
    selected_sym = request.args.get('chart', 'NIFTY50')
    rows = ""
    
    # वॉचलिस्ट बनाना
    for name, ticker in SYMBOLS.items():
        df = get_data(ticker)
        if not df.empty:
            last = df.iloc[-1]
            prev = df['close'].iloc[-2]
            color = "#00ff00" if last['close'] > last['ema9'] else "#ff4444"
            sig = "BUY" if last['close'] > last['ema9'] else "SELL"
            
            # नाम पर क्लिक करने के लिए लिंक बनाया
            rows += f"""
            <tr class='symbol-row' style='border-bottom:1px solid #333; cursor:pointer;' onclick="window.location.href='/?chart={name}'">
                <td style='padding:12px;'><b>{name}</b></td>
                <td>{last['open']:,.2f}</td>
                <td style='color:#00d1ff;'>{last['close']:,.2f}</td>
                <td>{prev:,.2f}</td>
                <td style='color:{color}; font-weight:bold;'>{sig}</td>
            </tr>"""

    # चयनित सिम्बल का चार्ट बनाना
    df_chart = get_data(SYMBOLS.get(selected_sym, "^NSEI"))
    chart_html = ""
    if not df_chart.empty:
        fig = go.Figure(data=[go.Candlestick(x=df_chart.index, open=df_chart['open'], high=df_chart['high'], low=df_chart['low'], close=df_chart['close'], name="Price")])
        fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['ema9'], line=dict(color='yellow', width=1), name='EMA 9'))
        fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['ema15'], line=dict(color='cyan', width=1), name='EMA 15'))
        fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['ema200'], line=dict(color='red', width=1.5), name='EMA 200'))
        fig.update_layout(template="plotly_dark", height=500, margin=dict(l=0,r=0,t=0,b=0), xaxis_rangeslider_visible=False)
        chart_html = fig.to_html(full_html=False)

    return f"""
    <html>
    <head>
        <meta http-equiv="refresh" content="60">
        <style>
            body {{ background:#0e1117; color:white; font-family:sans-serif; padding:20px; }}
            .card {{ background:#1a1c24; border-radius:12px; padding:20px; border:1px solid #333; }}
            input {{ background:#2d2f3b; border:1px solid #444; color:white; padding:10px; border-radius:5px; width:100%; margin-bottom:15px; }}
            th {{ text-align:left; color:#888; font-size:12px; padding-bottom:10px; }}
            .symbol-row:hover {{ background: #2d2f3b; }}
        </style>
    </head>
    <body>
        <h2 style='text-align:center; color:#00d1ff;'>🚀 NEXT-GEN TRADING HUB PRO</h2>
        <div style="display:flex; gap:20px; flex-wrap:wrap;">
            <div class="card" style="flex:1; min-width:350px; max-height: 600px; overflow-y: auto;">
                <h3>Live Watchlist</h3>
                <input type="text" id="searchInput" onkeyup="filter()" placeholder="Search Symbol...">
                <table style='width:100%; border-collapse: collapse;'>
                    <tr><th>SYMBOL</th><th>OPEN</th><th>LTP</th><th>PREV CLOSE</th><th>SIGNAL</th></tr>
                    {rows}
                </table>
            </div>
            <div class="card" style="flex:2; min-width:500px;">
                <h3>Live Chart: {selected_sym}</h3>
                {chart_html if chart_html else "Loading Chart..."}
            </div>
        </div>
        <script>
            function filter() {{
                let val = document.getElementById('searchInput').value.toUpperCase();
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












