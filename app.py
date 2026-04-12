from flask import Flask
import requests
import pandas as pd
import plotly.graph_objs as go

app = Flask(__name__)

SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT"]

HEADERS = {"User-Agent": "Mozilla/5.0"}

# ================= DATA =================
def get_data(symbol, interval):

    interval_map = {"15m": "15", "1h": "60", "4h": "240"}

    # ===== BINANCE =====
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

    # ===== BYBIT =====
    try:
        res = requests.get(
            "https://api.bybit.com/v5/market/kline",
            params={
                "category": "linear",
                "symbol": symbol,
                "interval": interval_map[interval],
                "limit": 200
            },
            timeout=5
        )

        data = res.json().get("result", {}).get("list", [])
        if data:
            df = pd.DataFrame(data, columns=[
                "time","open","high","low","close","volume","turnover"
            ])
            df = df[::-1]
            df = df[["open","high","low","close"]].apply(pd.to_numeric)
            return df
    except:
        pass

    # ===== OKX =====
    try:
        res = requests.get(
            "https://www.okx.com/api/v5/market/candles",
            params={
                "instId": symbol.replace("USDT", "-USDT"),
                "bar": interval,
                "limit": 200
            },
            timeout=5
        )

        data = res.json().get("data", [])
        if data:
            df = pd.DataFrame(data, columns=[
                "time","open","high","low","close","a","b","c","d"
            ])
            df = df[::-1]
            df = df[["open","high","low","close"]].apply(pd.to_numeric)
            return df
    except:
        pass

    # ===== KUCOIN =====
    try:
        res = requests.get(
            "https://api.kucoin.com/api/v1/market/candles",
            params={
                "symbol": symbol.replace("USDT", "-USDT"),
                "type": interval,
                "limit": 200
            },
            timeout=5
        )

        data = res.json().get("data", [])
        if data:
            df = pd.DataFrame(data, columns=[
                "time","open","close","high","low","volume","turnover"
            ])
            df = df[::-1]
            df = df[["open","high","low","close"]].apply(pd.to_numeric)
            return df
    except:
        pass

    return pd.DataFrame()


# ================= EMA =================
def apply_ema(df):
    if df.empty:
        return df
    df["ema9"] = df["close"].ewm(span=9).mean()
    df["ema15"] = df["close"].ewm(span=15).mean()
    df["ema200"] = df["close"].ewm(span=200).mean()
    return df


# ================= STRATEGY (UNCHANGED) =================
def trend(df):
    if df.empty or len(df) < 3:
        return "SIDE"
    last = df.iloc[-1]
    if last["close"] > last["ema9"] > last["ema15"] > last["ema200"]:
        return "UP"
    elif last["close"] < last["ema9"] < last["ema15"] < last["ema200"]:
        return "DOWN"
    return "SIDE"


def swing(df):
    if df.empty or len(df) < 3:
        return "NONE"
    highs = df["high"]
    lows = df["low"]
    if highs.iloc[-1] > highs.iloc[-2] > highs.iloc[-3]:
        return "HH"
    elif lows.iloc[-1] < lows.iloc[-2] < lows.iloc[-3]:
        return "LL"
    return "NONE"


def prev_day(df):
    if df.empty:
        return 0
    return df["close"].iloc[-24] if len(df) >= 24 else df["close"].iloc[-1]


def advanced_pullback(df):
    if df.empty:
        return None, None

    curr = df.iloc[-1]
    body = abs(curr["close"] - curr["open"])
    lower_wick = curr["open"] - curr["low"]
    upper_wick = curr["high"] - curr["close"]

    if curr["close"] > curr["ema200"] and curr["ema9"] > curr["ema15"] and lower_wick > body*1.5:
        return "BUY (PB)", "green"

    elif curr["close"] < curr["ema200"] and curr["ema9"] < curr["ema15"] and upper_wick > body*1.5:
        return "SELL (PB)", "red"

    return None, None


def strategy(symbol):
    df15 = apply_ema(get_data(symbol, "15m"))
    df1h = apply_ema(get_data(symbol, "1h"))
    df4h = apply_ema(get_data(symbol, "4h"))

    if df15.empty:
        return "NO DATA", "red", 0,0,0,0

    if df1h.empty: df1h = df15
    if df4h.empty: df4h = df15

    t15, t1h, t4h = trend(df15), trend(df1h), trend(df4h)
    sw = swing(df15)
    pd_level = prev_day(df1h)

    last = df15.iloc[-1]
    o,h,l,c = last["open"], last["high"], last["low"], last["close"]

    pb, color = advanced_pullback(df15)
    if pb:
        return pb, color, o,h,l,c

    if t15=="UP" and t1h=="UP" and t4h=="UP" and sw=="HH" and c>pd_level:
        return "BUY","green",o,h,l,c

    elif t15=="DOWN" and t1h=="DOWN" and t4h=="DOWN" and sw=="LL" and c<pd_level:
        return "SELL","red",o,h,l,c

    return "-", "white", o,h,l,c


# ================= CHART =================
def get_chart():
    df = apply_ema(get_data("BTCUSDT","15m"))
    if df.empty:
        return "<h3>No Chart</h3>"

    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=df.index, open=df['open'], high=df['high'],
        low=df['low'], close=df['close']
    ))
    fig.add_trace(go.Scatter(x=df.index,y=df['ema9']))
    fig.add_trace(go.Scatter(x=df.index,y=df['ema15']))
    fig.add_trace(go.Scatter(x=df.index,y=df['ema200']))
    fig.update_layout(template="plotly_dark", height=500)

    return fig.to_html(full_html=False)


# ================= UI =================
@app.route("/")
def dashboard():

    rows = ""
    for sym in SYMBOLS:
        signal,color,o,h,l,c = strategy(sym)

        rows += f"""
        <tr>
            <td>{sym}</td>
            <td>O:{o:.2f} H:{h:.2f} L:{l:.2f} C:{c:.2f}</td>
            <td style='color:{color}'>{signal}</td>
        </tr>
        """

    return f"""
    <html>
    <head>
        <meta http-equiv="refresh" content="10">
    </head>

    <body style="background:#0e1117;color:white;font-family:sans-serif">

    <h2>🚀 FINAL TRADING DASHBOARD</h2>

    <div style="display:flex;gap:20px">

        <div style="width:30%">
            <table border="1" cellpadding="10">
                <tr><th>COIN</th><th>OHLC</th><th>SIGNAL</th></tr>
                {rows}
            </table>
        </div>

        <div style="width:70%">
            {get_chart()}
        </div>

    </div>

    </body>
    </html>
    """


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT",10000))
    app.run(host="0.0.0.0", port=port)
