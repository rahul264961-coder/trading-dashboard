from flask import Flask, request, render_template_string
import yfinance as yf
import pandas as pd
import plotly.graph_objs as go
from plotly.subplots import make_subplots
import os
from datetime import datetime

# अपनी बनाई हुई फ़ाइलों को इम्पोर्ट करना
from strategy import apply_indicators, get_final_signal
from watchlist import WATCHLIST_GROUPS, SECTOR_COMPONENTS

app = Flask(__name__)

# --- डेटा फेचिंग इंजन (Multi-Timeframe Support) ---
def get_mtf_data(ticker):
    data_dict = {}
    for tf in ["5m", "15m", "1h", "4h"]:
        period = "2d" if tf in ["5m", "15m"] else "1mo"
        try:
            df = yf.download(ticker, period=period, interval=tf, progress=False)
            if not df.empty:
                df.columns = [c.lower() for c in df.columns]
                data_dict[tf] = apply_indicators(df)
        except: pass
    return data_dict

# --- चार्ट जनरेटर (इमेज जैसा RSI + EMA लुक) ---
def generate_chart(ticker, interval):
    data = get_mtf_data(ticker)
    if interval not in data: return "<div>Chart Data Unavailable</div>"
    
    df = data[interval]
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])
    
    # Candlesticks
    fig.add_trace(go.Candlestick(x=df.index, open=df['open'], high=df['high'], low=df['low'], close=df['close'], name="Price"), row=1, col=1)
    # EMAs
    fig.add_trace(go.Scatter(x=df.index, y=df['ema9'], line=dict(color='yellow', width=1), name='EMA 9'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['ema15'], line=dict(color='cyan', width=1), name='EMA 15'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['ema200'], line=dict(color='red', width=1.5), name='EMA 200'), row=1, col=1)
    # RSI
    fig.add_trace(go.Scatter(x=df.index, y=df.get('rsi', []), line=dict(color='#7e57c2', width=1.5), name='RSI'), row=2, col=1)
    
    fig.update_layout(template="plotly_dark", height=500, margin=dict(l=0,r=0,t=0,b=0), xaxis_rangeslider_visible=False, paper_bgcolor='#131722', plot_bgcolor='#131722')
    return fig.to_html(full_html=False)

@app.route("/")
def index():
    active_tab = request.args.get('tab', 'Market Indices')
    selected_sym = request.args.get('symbol', '^NSEI')
    selected_tf = request.args.get('tf', '15m')
    
    # वॉचलिस्ट रोस बनाना
    rows = ""
    for name, ticker in WATCHLIST_GROUPS[active_tab].items():
        data = get_mtf_data(ticker)
        if '15m' in data:
            df = data['15m']
            last = df.iloc[-1]
            # आपकी strategy.py से सिग्नल लेना
            signal, color = get_final_signal(data)
            
            rows += f"""
            <tr class='symbol-row' onclick="window.location.href='/?tab={active_tab}&symbol={ticker}&tf={selected_tf}'" style='cursor:pointer;'>
                <td><b>{name}</b></td>
                <td>{last['open']:,.1f}</td><td>{last['high']:,.1f}</td>
                <td>{last['low']:,.1f}</td><td style='color:#00d1ff;'>{last['close']:,.1f}</td>
                <td style='color:{color}; font-weight:bold;'>{signal}</td>
            </tr>"""

    # UI रेंडर करना
    return f"""
    <html>
    <head>
        <meta http-equiv="refresh" content="60">
        <style>
            body {{ background:#0e1117; color:white; font-family:sans-serif; margin:0; padding:20px; }}
            .card {{ background:#1a1c24; border-radius:12px; padding:15px; border:1px solid #333; }}
            .btn {{ background:#333; color:white; border:none; padding:8px 12px; cursor:pointer; border-radius:5px; margin-right:5px; font-size:12px; }}
            .active {{ background:#00d1ff; color:black; font-weight:bold; }}
            table {{ width:100%; text-align:left; border-collapse: collapse; font-size:12px; }}
            td, th {{ padding:12px 10px; border-bottom:1px solid #222; }}
            .symbol-row:hover {{ background:#2d2f3b; }}
            input {{ width:100%; padding:10px; margin-bottom:15px; background:#2d2f3b; border:1px solid #444; color:white; border-radius:5px; }}
        </style>
    </head>
    <body>
        <h2 style='text-align:center; color:#00d1ff;'>🚀 ULTIMATE TRADING HUB</h2>
        
        <!-- Watchlist Tabs -->
        <div style="margin-bottom:15px; text-align:center;">
            {' '.join([f"<button class='btn {'active' if t==active_tab else ''}' onclick=\\\"window.location.href='/?tab={t}&symbol={selected_sym}&tf={selected_tf}'\\\">{t}</button>" for t in WATCHLIST_GROUPS.keys()])}
        </div>

        <div style="display:flex; gap:20px; flex-wrap:wrap;">
            <!-- Watchlist Section with OHLC and Signal -->
            <div class="card" style="flex:1.2; min-width:380px; max-height:700px; overflow-y:auto;">
                <input type="text" id="srch" onkeyup="filter()" placeholder="Search symbols in {active_tab}...">
                <table>
                    <tr><th>SYMBOL</th><th>O</th><th>H</th><th>L</th><th>C</th><th>SIGNAL</th></tr>
                    {rows}
                </table>
            </div>

            <!-- Chart Section with Timeframes -->
            <div class="card" style="flex:2.5; min-width:550px;">
                <div style="display:flex; justify-content:space-between; margin-bottom:10px;">
                    <h3 style='margin:0;'>{selected_sym}</h3>
                    <div>
                        {' '.join([f"<button class='btn {'active' if tf==selected_tf else ''}' onclick=\\\"window.location.href='/?tab={active_tab}&symbol={selected_sym}&tf={tf}'\\\">{tf}</button>" for tf in ["5m","15m","1h","4h","1d"]])}
                    </div>
                </div>
                {generate_chart(selected_sym, selected_tf)}
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
    </html>
    """

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

















