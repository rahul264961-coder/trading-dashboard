from flask import Flask, request
import requests
import pandas as pd
import plotly.graph_objs as go
import yfinance as yf
from datetime import datetime

app = Flask(__name__)

SYMBOLS = {
    "NIFTY50": "^NSEI", "BANKNIFTY": "^NSEBANK", "FINNIFTY": "NIFTY_FIN_SERVICE.NS", 
    "SENSEX": "^BSESN", "MIDCAP_NIFTY": "NIFTY_MID_SELECT.NS", "INDIA_VIX": "^INDIAVIX",
    "BTCUSDT": "BTC-USD", "ETHUSDT": "ETH-USD", "SOLUSDT": "SOL-USD", "PAXG_GOLD": "PAXG-USD"
}

def get_data(ticker, interval="15m"):
    # छोटे टाइमफ्रेम के लिए कम दिनों का डेटा ताकि लोड जल्दी हो
    period = "1d" if interval in ["1m", "3m", "5m"] else "5d"
    try:
        data = yf.download(ticker, period=period, interval=interval, progress=False)
        if not data.empty:
            df = data[['Open', 'High', 'Low', 'Close']].copy()
            df.columns = ["open", "high", "low", "close"]
            # EMA Calculation
            df["ema9"] = df["close"].ewm(span=9).mean()
            df["ema15"] = df["close"].ewm(span=15).mean()
            df["ema200"] = df["close"].ewm(span=200).mean()
            return df
    except: pass
    return pd.DataFrame()

@app.route("/")
def dashboard():
    selected_sym = request.args.get('chart', 'NIFTY50')
    selected_tf = request.args.get('tf', '15m') # डिफॉल्ट टाइमफ्रेम 15m
    
    rows = ""
    for name, ticker in SYMBOLS.items():
        # वॉचलिस्ट के लिए हमेशा 15m डेटा इस्तेमाल करेंगे
        df_watch = get_data(ticker, "15m")
        if not df_watch.empty:
            last = df_watch.iloc[-1]
            rows += f"""
            <tr class='symbol-row' onclick="window.location.href='/?chart={name}&tf={selected_tf}'">
                <td><b>{name}</b></td>
                <td style='color:#00d1ff;'>{last['close']:,.2f}</td>
            </tr>"""

    # चयनित सिम्बल और टाइमफ्रेम का चार्ट
    df_chart = get_data(SYMBOLS.get(selected_sym, "^NSEI"), selected_tf)
    chart_html = ""
    if not df_chart.empty:
        fig = go.Figure(data=[go.Candlestick(
            x=df_chart.index, open=df_chart['open'], high=df_chart['high'],
            low=df_chart['low'], close=df_chart['close'], name="Candles"
        )])
        # EMA Lines
        fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['ema9'], line=dict(color='#FFD700', width=1.5), name='EMA 9'))
        fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['ema15'], line=dict(color='#00FFFF', width=1.5), name='EMA 15'))
        fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['ema200'], line=dict(color='#FF4500', width=2), name='EMA 200'))
        
        fig.update_layout(
            template="plotly_dark", height=550, margin=dict(l=10,r=10,t=10,b=10),
            xaxis_rangeslider_visible=False,
            # लाइव फील के लिए एनीमेशन सेटिंग्स
            uirevision='constant' 
        )
        chart_html = fig.to_html(full_html=False)

    # टाइमफ्रेम बटन्स का HTML
    tf_buttons = ""
    for tf in ["1m", "3m", "5m", "15m", "1h", "4h", "1d"]:
        active_style = "background:#00d1ff; color:black;" if tf == selected_tf else "background:#333; color:white;"
        tf_buttons += f"<button onclick=\"window.location.href='/?chart={selected_sym}&tf={tf}'\" style='{active_style} border:none; padding:8px 12px; margin-right:5px; border-radius:4px; cursor:pointer;'>{tf}</button>"

    return f"""
    <html>
    <head>
        <meta http-equiv="refresh" content="15"> <!-- रिफ्रेश रेट 15 सेकंड किया ताकि लाइव लगे -->
        <style>
            body {{ background:#0e1117; color:white; font-family:sans-serif; margin:0; padding:20px; }}
            .container {{ display:flex; gap:20px; }}
            .card {{ background:#1a1c24; border-radius:12px; padding:20px; border:1px solid #333; }}
            .symbol-row:hover {{ background: #2d2f3b; cursor:pointer; }}
            table {{ width:100%; border-collapse: collapse; }}
            th {{ text-align:left; color:#888; font-size:12px; padding-bottom:10px; }}
            td {{ padding:10px 0; border-bottom:1px solid #333; }}
        </style>
    </head>
    <body>
        <h2 style='text-align:center; color:#00d1ff;'>🚀 PRO LIVE TERMINAL</h2>
        <div class="container">
            <div class="card" style="width:250px;">
                <h3>Watchlist</h3>
                <table>{rows}</table>
            </div>
            <div class="card" style="flex:1;">
                <div style="display:flex; justify-content:space-between; margin-bottom:15px;">
                    <h3>{selected_sym} ({selected_tf})</h3>
                    <div>{tf_buttons}</div>
                </div>
                {chart_html if chart_html else "Loading Live Data..."}
            </div>
        </div>
    </body>
    </html>
    """

if __name__ == "__main__":
    import os
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))













