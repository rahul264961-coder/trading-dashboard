from flask import Flask, request
import pandas as pd
import plotly.graph_objs as go
from plotly.subplots import make_subplots
import yfinance as yf
from datetime import datetime

app = Flask(__name__)

WATCHLISTS = {
    "Indices": ["^NSEI", "^NSEBANK", "^BSESN", "^INDIAVIX"],
    "Crypto": ["BTC-USD", "ETH-USD", "SOL-USD", "XRP-USD"],
    "Sectors": ["NIFTY_FIN_SERVICE.NS", "^CNXIT", "^CNXPHARMA", "^CNXAUTO"],
    "Global/Gold": ["PAXG-USD", "GC=F", "CL=F"],
    "Favorites": ["RELIANCE.NS", "HDFCBANK.NS", "TCS.NS"]
}

# ================= 🛡️ ADVANCED STRATEGY ENGINE =================
def get_detailed_data(ticker, interval):
    p_map = {"1m":"1d", "5m":"1d", "15m":"5d", "1h":"1mo", "4h":"1mo", "1d":"6mo"}
    try:
        df = yf.download(ticker, period=p_map.get(interval, "5d"), interval=interval, progress=False)
        if df.empty: return df
        df.columns = [c.lower() for c in df.columns]
        df["ema9"] = df['close'].ewm(span=9).mean()
        df["ema15"] = df['close'].ewm(span=15).mean()
        df["ema200"] = df['close'].ewm(span=200).mean()
        return df
    except: return pd.DataFrame()

def analyze_strategy(ticker):
    # Multi-Timeframe Check (5m, 15m, 1h, 4h)
    timeframes = ["5m", "15m", "1h", "4h"]
    tf_results = {}
    
    for tf in timeframes:
        df = get_detailed_data(ticker, tf)
        if df.empty or len(df) < 5: continue
        
        last = df.iloc[-2] # Closed Candle
        curr = df.iloc[-1]
        
        # 1. EMA TREND
        up_trend = last['close'] > last['ema9'] > last['ema15'] > last['ema200']
        down_trend = last['close'] < last['ema9'] < last['ema15'] < last['ema200']
        
        # 2. SWING STRUCTURE (HH/LL)
        hh = df['high'].iloc[-2] > df['high'].iloc[-3] > df['high'].iloc[-4]
        ll = df['low'].iloc[-2] < df['low'].iloc[-3] < df['low'].iloc[-4]
        
        # 3. PULLBACK LOGIC
        body = abs(last['close'] - last['open'])
        lower_wick = last['open'] - last['low'] if last['close'] > last['open'] else last['close'] - last['low']
        upper_wick = last['high'] - last['close'] if last['close'] > last['open'] else last['high'] - last['open']
        
        pb_buy = (last['low'] <= last['ema15'] * 1.001) and lower_wick > body * 1.5 and up_trend
        pb_sell = (last['high'] >= last['ema15'] * 0.999) and upper_wick > body * 1.5 and down_trend
        
        if pb_buy: tf_results[tf] = "PULL_BUY"
        elif pb_sell: tf_results[tf] = "PULL_SELL"
        elif up_trend and hh: tf_results[tf] = "BUY"
        elif down_trend and ll: tf_results[tf] = "SELL"
        else: tf_results[tf] = "SIDE"

    # Final Decision
    if all(tf_results.get(t) in ["BUY", "PULL_BUY"] for t in ["5m", "15m"]):
        return "STRONG BUY", "#00ff00"
    elif all(tf_results.get(t) in ["SELL", "PULL_SELL"] for t in ["5m", "15m"]):
        return "STRONG SELL", "#ff4444"
    return "SIDEWAYS", "gray"

# ================= UI & DASHBOARD =================
@app.route("/")
def dashboard():
    selected_sym = request.args.get('chart', '^NSEI')
    active_tab = request.args.get('tab', 'Indices')
    selected_tf = request.args.get('tf', '15m')
    
    rows = ""
    for ticker in WATCHLISTS[active_tab]:
        df_row = get_detailed_data(ticker, "15m")
        if not df_row.empty:
            last = df_row.iloc[-1]
            sig, col = analyze_strategy(ticker) # आपकी स्ट्रेटजी यहाँ कॉल हो रही है
            rows += f"""
            <tr class='symbol-row' onclick=\"window.location.href='/?chart={ticker}&tab={active_tab}&tf={selected_tf}'\" style='cursor:pointer;'>
                <td><b>{ticker}</b></td>
                <td>{last['open']:,.1f}</td><td>{last['high']:,.1f}</td>
                <td>{last['low']:,.1f}</td><td style='color:#00d1ff;'>{last['close']:,.1f}</td>
                <td style='color:{col}; font-weight:bold;'>{sig}</td>
            </tr>"""

    # UI Buttons & Chart (Subplots with RSI)
    tf_btns = "".join([f"<button class='tf-btn {'active-tf' if t==selected_tf else ''}' onclick=\"window.location.href='/?chart={selected_sym}&tab={active_tab}&tf={t}'\">{t}</button>" for t in ["1m","5m","15m","1h","4h","1d"]])
    tab_btns = "".join([f"<button class='tab-btn {'active-tab' if t==active_tab else ''}' onclick=\"window.location.href='/?tab={t}&chart={selected_sym}&tf={selected_tf}'\">{t}</button>" for t in WATCHLISTS.keys()])

    # Chart Generation
    df_chart = get_detailed_data(selected_sym, selected_tf)
    chart_html = "Loading Chart..."
    if not df_chart.empty:
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])
        fig.add_trace(go.Candlestick(x=df_chart.index, open=df_chart['open'], high=df_chart['high'], low=df_chart['low'], close=df_chart['close'], name="Price"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['ema9'], line=dict(color='yellow', width=1), name='EMA 9'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['ema200'], line=dict(color='red', width=1.5), name='EMA 200'), row=1, col=1)
        fig.update_layout(template="plotly_dark", height=500, margin=dict(l=0,r=0,t=0,b=0), xaxis_rangeslider_visible=False)
        chart_html = fig.to_html(full_html=False)

    return f"""
    <html>
    <head><meta http-equiv="refresh" content="60">
    <style>
        body {{ background:#0e1117; color:white; font-family:sans-serif; margin:0; padding:20px; }}
        .card {{ background:#1a1c24; border-radius:12px; padding:15px; border:1px solid #333; }}
        .tab-btn, .tf-btn {{ background:#333; color:white; border:none; padding:8px 12px; cursor:pointer; border-radius:5px; margin-right:5px; }}
        .active-tab, .active-tf {{ background:#00d1ff; color:black; font-weight:bold; }}
        table {{ width:100%; text-align:left; border-collapse: collapse; font-size:12px; }}
        td {{ padding:10px; border-bottom:1px solid #222; }}
        .symbol-row:hover {{ background:#2d2f3b; }}
    </style>
    </head>
    <body>
        <h2 style='text-align:center; color:#00d1ff;'>🚀 NEXT-GEN TRADING HUB PRO</h2>
        <div style="margin-bottom:15px; text-align:center;">{tab_btns}</div>
        <div style="display:flex; gap:20px; flex-wrap:wrap;">
            <div class="card" style="flex:1.2; min-width:380px; max-height:650px; overflow-y:auto;">
                <input type="text" id="srch" onkeyup="filter()" placeholder="Search..." style="width:100%; padding:10px; margin-bottom:15px; background:#2d2f3b; border:1px solid #444; color:white; border-radius:5px;">
                <table><tr><th>SYMBOL</th><th>O</th><th>H</th><th>L</th><th>C</th><th>SIGNAL</th></tr>{rows}</table>
            </div>
            <div class="card" style="flex:2.5; min-width:550px;">
                <div style="display:flex; justify-content:space-between; margin-bottom:10px;">
                    <h3 style='margin:0;'>{selected_sym}</h3><div>{tf_btns}</div>
                </div>
                {chart_html}
            </div>
        </div>
    </body>
    </html>"""

if __name__ == "__main__":
    import os
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))

















