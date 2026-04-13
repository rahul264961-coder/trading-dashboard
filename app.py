from flask import Flask, request
import pandas as pd
import plotly.graph_objs as go
import yfinance as yf
from datetime import datetime

app = Flask(__name__)

# सेक्टर और उनके मुख्य स्टॉक्स की लिस्ट
SECTORS = {
    "BANKING": ["HDFCBANK.NS", "ICICIBANK.NS", "SBIN.NS", "KOTAKBANK.NS", "AXISBANK.NS"],
    "IT SECTOR": ["TCS.NS", "INFY.NS", "WIPRO.NS", "HCLTECH.NS", "TECHM.NS"],
    "AUTO": ["TATAMOTORS.NS", "M&M.NS", "MARUTI.NS", "EICHERMOT.NS"],
    "PHARMA": ["SUNPHARMA.NS", "CIPLA.NS", "DRREDDY.NS", "DIVISLAB.NS"],
    "RELIANCE/ENERGY": ["RELIANCE.NS", "ONGC.NS", "NTPC.NS", "POWERGRID.NS"]
}

WATCHLISTS = {
    "Indices": ["^NSEI", "^NSEBANK", "^BSESN", "^INDIAVIX"],
    "Crypto": ["BTC-USD", "ETH-USD", "SOL-USD", "XRP-USD"],
    "Global": ["PAXG-USD", "GC=F", "CL=F"]
}

def get_sector_status():
    sector_data = []
    for name, stocks in SECTORS.items():
        changes = []
        for s in stocks:
            try:
                d = yf.download(s, period="1d", interval="15m", progress=False)
                if not d.empty:
                    # % बदलाव निकालना
                    change = ((d['Close'].iloc[-1] - d['Open'].iloc[0]) / d['Open'].iloc[0]) * 100
                    changes.append(change)
            except: continue
        
        if changes:
            avg_change = sum(changes) / len(changes)
            color = "#00ff00" if avg_change > 0 else "#ff4444"
            status = "STRONG 🔥" if avg_change > 0.5 else ("WEAK 📉" if avg_change < -0.5 else "NEUTRAL ⚖️")
            sector_data.append({"name": name, "change": avg_change, "color": color, "status": status})
    return sector_data

@app.route("/")
def dashboard():
    selected_sym = request.args.get('chart', '^NSEI')
    active_tab = request.args.get('tab', 'Indices')
    
    # सेक्टर हीटमैप का HTML बनाना
    sectors = get_sector_status()
    sector_html = ""
    for s in sectors:
        sector_html += f"""
        <div style="background:{s['color']}22; border:1px solid {s['color']}; padding:10px; border-radius:8px; flex:1; min-width:150px; text-align:center;">
            <div style="font-size:12px; color:#888;">{s['name']}</div>
            <div style="font-size:16px; font-weight:bold; color:{s['color']};">{s['change']:.2f}%</div>
            <div style="font-size:10px;">{s['status']}</div>
        </div>
        """

    # ... (बाकी का Watchlist और Chart लॉजिक पहले जैसा ही रहेगा) ...

    return f"""
    <html>
    <head><meta http-equiv="refresh" content="60">
    <style>
        body {{ background:#0e1117; color:white; font-family:sans-serif; padding:20px; }}
        .card {{ background:#1a1c24; border-radius:12px; padding:15px; border:1px solid #333; }}
        .heatmap-container {{ display:flex; gap:10px; margin-bottom:20px; flex-wrap:wrap; }}
    </style>
    </head>
    <body>
        <h2 style='text-align:center; color:#00d1ff;'>🚀 NEXT-GEN TRADING TERMINAL</h2>
        
        <!-- SECTOR HEATMAP SECTION -->
        <h3 style="margin-bottom:10px; font-size:16px;">Sector Strength Heatmap</h3>
        <div class="heatmap-container">{sector_html}</div>

        <div style="display:flex; gap:20px; flex-wrap:wrap;">
            <!-- Watchlist & Chart Logic -->
            <div class="card" style="flex:1; min-width:350px;">
                <h3>Watchlist</h3>
                <!-- आपकी वॉचलिस्ट टेबल यहाँ आएगी -->
            </div>
            <div class="card" style="flex:2;">
                <h3>Market Chart</h3>
                <!-- आपका चार्ट यहाँ आएगा -->
            </div>
        </div>
    </body>
    </html>
    """

if __name__ == "__main__":
    import os
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))

















