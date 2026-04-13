from flask import Flask, request
import pandas as pd
import plotly.graph_objs as go
from plotly.subplots import make_subplots
import yfinance as yf
from datetime import datetime

app = Flask(__name__)

# आपकी वॉचलिस्ट का डेटा (इसे मैंने वैसा ही रखा है)
WATCHLISTS = {
    "Indices": ["^NSEI", "^NSEBANK", "^BSESN", "^INDIAVIX"],
    "Crypto": ["BTC-USD", "ETH-USD", "SOL-USD", "XRP-USD"],
    "Sectors": ["NIFTY_FIN_SERVICE.NS", "^CNXIT", "^CNXPHARMA", "^CNXAUTO"],
    "Global/Gold": ["PAXG-USD", "GC=F", "CL=F"],
    "Favorites": ["RELIANCE.NS", "HDFCBANK.NS", "TCS.NS"]
}

def get_data(ticker, interval="15m"):
    period_map = {"1m":"1d", "3m":"1d", "5m":"1d", "15m":"5d", "1h":"1mo", "4h":"1mo", "1d":"6mo"}
    p = period_map.get(interval, "5d")
    try:
        data = yf.download(ticker, period=p, interval=interval, progress=False)
        if not data.empty:
            df = data[['Open', 'High', 'Low', 'Close']].copy()
            df.columns = ["open", "high", "low", "close"]
            # EMA calculations
            df["ema9"] = df["close"].ewm(span=9).mean()
            df["ema15"] = df["close"].ewm(span=15).mean()
            df["ema200"] = df["close"].ewm(span=200).mean()
            # RSI calculation
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            df['rsi'] = 100 - (100 / (1 + (gain / loss)))
            return df
    except: pass
    return pd.DataFrame()

def get_chart_html(ticker, interval):
    df = get_data(ticker, interval)
    if df.empty: return "<div style='color:orange; padding:50px;'>No Chart Data Available</div>"
    
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])
    fig.add_trace(go.Candlestick(x=df.index, open=df['open'], high=df['high'], low=df['low'], close=df['close'], name="Price"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['ema9'], line=dict(color='#26a69a', width=1), name='EMA 9'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['ema15'], line=dict(color='#2962ff', width=1), name='EMA 15'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['ema200'], line=dict(color='#f44336', width=1.5), name='EMA 200'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['rsi'], line=dict(color='#7e57c2', width=1.5), name='RSI'), row=2, col=1)
    
    fig.update_layout(template="plotly_dark", height=500, margin=dict(l=0,r=0,t=0,b=0), xaxis_rangeslider_visible=False, paper_bgcolor='#131722', plot_bgcolor='#131722')
    return fig.to_html(full_html=False)

@app.route("/")
def dashboard():
    # URL से जानकारी उठाना
    selected_sym = request.args.get('chart', '^NSEI')
    active_tab = request.args.get('tab', 'Indices')
    selected_tf = request.args.get('tf', '15m')
    
    rows = ""
    for ticker in WATCHLISTS[active_tab]:
        df_row = get_data(ticker, "15m")
        if not df_row.empty:
            last = df_row.iloc[-1]
            # यहाँ URL में tab और tf दोनों जोड़ दिए ताकि वॉचलिस्ट न बदले
            rows += f"<tr class='symbol-row' onclick=\"window.location.href='/?chart={ticker}&tab={active_tab}&tf={selected_tf}'\" style='cursor:pointer;'><td><b>{ticker}</b></td><td>{last['open']:,.1f}</td><td>{last['high']:,.1f}</td><td>{last['low']:,.1f}</td><td style='color:#00d1ff;'>{last['close']:,.1f}</td></tr>"

    # Tab और Timeframe बटन के लिए लिंक फिक्स किए गए
    tab_btns = "".join([f"<button class='tab-btn {'active-tab' if t==active_tab else ''}' onclick=\"window.location.href='/?tab={t}&chart={selected_sym}&tf={selected_tf}'\">{t}</button>" for t in WATCHLISTS.keys()])
    tf_btns = "".join([f"<button class='tf-btn {'active-tf' if t==selected_tf else ''}' onclick=\"window.location.href='/?chart={selected_sym}&tab={active_tab}&tf={t}'\">{t}</button>" for t in ["1m","3m","5m","15m","1h","4h","1d"]])

    return f"""
    <html>
    <head><meta http-equiv="refresh" content="60">
    <style>
        body {{ background:#0e1117; color:white; font-family:sans-serif; margin:0; padding:20px; }}
        .card {{ background:#1a1c24; border-radius:12px; padding:15px; border:1px solid #333; }}
        .tab-btn, .tf-btn {{ background:#333; color:white; border:none; padding:8px 12px; cursor:pointer; border-radius:5px; margin-right:5px; }}
        .active-tab {{ background:#00d1ff; color:black; font-weight:bold; }}
        .active-tf {{ background:#00d1ff; color:black; font-weight:bold; }}
        table {{ width:100%; text-align:left; border-collapse: collapse; font-size:13px; }}
        td {{ padding:12px 10px; border-bottom:1px solid #222; }}
        .symbol-row:hover {{ background:#2d2f3b; }}
    </style>
    </head>
    <body>
        <h2 style='text-align:center; color:#00d1ff;'>🚀 NEXT-GEN TRADING HUB PRO</h2>
        <div style="margin-bottom:15px; text-align:center;">{tab_btns}</div>
        <div style="display:flex; gap:20px; flex-wrap:wrap;">
            <div class="card" style="flex:1; min-width:350px; max-height:650px; overflow-y:auto;">
                <input type="text" id="srch" onkeyup="filter()" placeholder="Search symbols..." style="width:100%; padding:10px; margin-bottom:15px; background:#2d2f3b; border:1px solid #444; color:white; border-radius:5px;">
                <table><tr><th>SYMBOL</th><th>O</th><th>H</th><th>L</th><th>C</th></tr>{rows}</table>
            </div>
            <div class="card" style="flex:2.5; min-width:550px;">
                <div style="display:flex; justify-content:space-between; margin-bottom:10px;">
                    <h3 style='margin:0;'>{selected_sym} ({selected_tf})</h3>
                    <div>{tf_btns}</div>
                </div>
                {get_chart_html(selected_sym, selected_tf)}
            </div>
        </div>
        <script>
            function filter() {{
                let val = document.getElementById('srch').value.toUpperCase();
                let rows = document.getElementsByClassName('symbol-row');
                for (let r of rows) {{ r.style.display = r.innerText.toUpperCase().includes(val) ? "" : "none"; }}
            }}
        </script>
    </body>
    </html>"""

if __name__ == "__main__":
    import os
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))

















