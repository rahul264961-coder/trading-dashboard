from flask import Flask
import requests
import pandas as pd
import plotly.graph_objs as go

app = Flask(__name__)

# 1. यहाँ मैंने इंडियन इंडेक्स (Nifty/BankNifty) को लिस्ट में जोड़ दिया है
SYMBOLS = ["NIFTY50", "BANKNIFTY", "BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT"]

HEADERS = {"User-Agent": "Mozilla/5.0"}

# ================= DATA =================
def get_data(symbol, interval):
    interval_map = {"15m": "15", "1h": "60", "4h": "240"}

    # --- INDIAN MARKET DATA (Yahoo Finance API for Nifty/BankNifty) ---
    if symbol in ["NIFTY50", "BANKNIFTY"]:
        ticker = "^NSEI" if symbol == "NIFTY50" else "^NSEBANK"
        try:
            # 15m डेटा के लिए Yahoo Finance का इस्तेमाल
            res = requests.get(f"https://yahoo.com{ticker}?interval={interval}&range=5d", headers=HEADERS)
            data = res.json()['chart']['result'][0]
            df = pd.DataFrame({
                "open": data['indicators']['quote'][0]['open'],
                "high": data['indicators']['quote'][0]['high'],
                "low": data['indicators']['quote'][0]['low'],
                "close": data['indicators']['quote'][0]['close']
            })
            return df.dropna().tail(200)
        except:
            return pd.DataFrame()

    # ===== BINANCE (Existing) =====
    try:
        res = requests.get(
            "https://api.binance.com/api/v3/klines",
            params={"symbol": symbol, "interval": interval, "limit": 200},
            headers=HEADERS, timeout=5
        )
        data = res.json()
        if isinstance(data, list) and len(data) > 0:
            df = pd.DataFrame(data, columns=[
                "time","open","high","low","close","volume",
                "ct","qav","nt","tbv","tqv","ignore"
            ])
            df = df[["open","high","low","close"]].apply(pd.to_numeric)
            return df
    except:
        pass
    
    # ... (बाकी के Bybit, OKX, Kucoin API वैसे ही रहेंगे जैसे आपने दिए थे) ...
    return pd.DataFrame()

# ================= EMA & STRATEGY (Unchanged) =================
def apply_ema(df):
    if df.empty: return df
    df["ema9"] = df["close"].ewm(span=9).mean()
    df["ema15"] = df["close"].ewm(span=15).mean()
    df["ema200"] = df["close"].ewm(span=200).mean()
    return df

def trend(df):
    if df.empty or len(df) < 3: return "SIDE"
    last = df.iloc[-1]
    if last["close"] > last["ema9"] > last["ema15"] > last["ema200"]: return "UP"
    elif last["close"] < last["ema9"] < last["ema15"] < last["ema200"]: return "DOWN"
    return "SIDE"

def swing(df):
    if df.empty or len(df) < 3: return "NONE"
    highs, lows = df["high"], df["low"]
    if highs.iloc[-1] > highs.iloc[-2] > highs.iloc[-3]: return "HH"
    elif lows.iloc[-1] < lows.iloc[-2] < lows.iloc[-3]: return "LL"
    return "NONE"

def prev_day(df):
    if df.empty: return 0
    return df["close"].iloc[-24] if len(df) >= 24 else df["close"].iloc[-1]

def advanced_pullback(df):
    if df.empty: return None, None
    curr = df.iloc[-1]
    body = abs(curr["close"] - curr["open"])
    lower_wick, upper_wick = curr["open"] - curr["low"], curr["high"] - curr["close"]
    if curr["close"] > curr["ema200"] and curr["ema9"] > curr["ema15"] and lower_wick > body*1.5:
        return "BUY (PB)", "green"
    elif curr["close"] < curr["ema200"] and curr["ema9"] < curr["ema15"] and upper_wick > body*1.5:
        return "SELL (PB)", "red"
    return None, None

def strategy(symbol):
    df15 = apply_ema(get_data(symbol, "15m"))
    if df15.empty: return "NO DATA", "red", 0,0,0,0
    
    t15 = trend(df15)
    sw = swing(df15)
    pd_level = prev_day(df15)
    last = df15.iloc[-1]
    o,h,l,c = last["open"], last["high"], last["low"], last["close"]

    pb, color = advanced_pullback(df15)
    if pb: return pb, color, o,h,l,c

    if t15=="UP" and sw=="HH" and c>pd_level: return "BUY","green",o,h,l,c
    elif t15=="DOWN" and sw=="LL" and c<pd_level: return "SELL","red",o,h,l,c

    return "-", "white", o,h,l,c

# ================= CHART =================
def get_chart():
    df = apply_ema(get_data("BTCUSDT","15m"))
    if df.empty: return "<h3>No Chart</h3>"

    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=df.index, open=df['open'], high=df['high'], low=df['low'], close=df['close'], name="Market"))
    fig.add_trace(go.Scatter(x=df.index, y=df['ema9'], name="EMA 9"))
    fig.add_trace(go.Scatter(x=df.index, y=df['ema200'], name="EMA 200"))
    
    # चार्ट को दाईं तरफ बेहतर दिखाने के लिए लेआउट सेटिंग्स
    fig.update_layout(template="plotly_dark", height=600, margin=dict(l=10, r=10, t=10, b=10))
    return fig.to_html(full_html=False)

# ================= UI =================
@app.route("/")
def dashboard():
    rows = ""
    for sym in SYMBOLS:
        signal, color, o, h, l, c = strategy(sym)
        rows += f"""
        <tr style='border-bottom: 1px solid #444;'>
            <td style='padding:15px;'><b>{sym}</b></td>
            <td><span style='color:#00ff00'>LTP: {c:.2f}</span><br><small>O:{o:.1f} H:{h:.1f} L:{l:.1f}</small></td>
            <td style='color:{color}; font-weight:bold;'>{signal}</td>
        </tr>
        """

    return f"""
    <html>
    <head><meta http-equiv="refresh" content="15"></head>
    <body style="background:#0e1117; color:white; font-family:sans-serif; margin:0; padding:20px;">
    
    <h2 style='text-align:center;'>🚀 PRO TRADING HUB (LIVE PRICE)</h2>

    <div style="display:flex; flex-direction: row; gap:20px;">
        
        <!-- LEFT SIDE: WATCHLIST -->
        <div style="width:35%; background:#1a1c24; border-radius:10px; padding:10px;">
            <h3 style='border-bottom:1px solid #555; padding-bottom:10px;'>Watchlist</h3>
            <table style='width:100%; border-collapse: collapse;'>
                <tr style='text-align:left; color:#888;'><th>SYMBOL</th><th>LIVE PRICE / OHLC</th><th>SIGNAL</th></tr>
                {rows}
            </table>
        </div>

        <!-- RIGHT SIDE: CHART -->
        <div style="width:65%; background:#1a1c24; border-radius:10px; padding:10px;">
            <h3 style='border-bottom:1px solid #555; padding-bottom:10px;'>Live Analysis</h3>
            {get_chart()}
        </div>

    </div>

    </body>
    </html>
    """

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

