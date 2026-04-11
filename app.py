from flask import Flask, request
import requests
import pandas as pd
import plotly.graph_objs as go

app = Flask(__name__)

SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "PAXGUSDT"]
BASE_URL = "https://api.binance.com/api/v3/klines"


# ================= DATA =================
def get_data(symbol, interval):
    params = {"symbol": symbol, "interval": interval, "limit": 200}

    try:
        res = requests.get(BASE_URL, params=params, timeout=5)
        data = res.json()
    except:
        return pd.DataFrame()

    if not data or isinstance(data, dict):
        return pd.DataFrame()

    df = pd.DataFrame(data, columns=[
        "time","open","high","low","close","volume",
        "ct","qav","nt","tbv","tqv","ignore"
    ])

    for col in ["open","high","low","close"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df.dropna(inplace=True)

    return df


# ================= EMA =================
def apply_ema(df):
    if df.empty:
        return df

    df["ema9"] = df["close"].ewm(span=9).mean()
    df["ema15"] = df["close"].ewm(span=15).mean()
    df["ema200"] = df["close"].ewm(span=200).mean()
    return df


# ================= SAFE TREND =================
def trend(df):
    if df.empty or len(df) < 3:
        return "SIDE"

    last = df.iloc[-1]

    if last["close"] > last["ema9"] > last["ema15"] > last["ema200"]:
        return "UP"
    elif last["close"] < last["ema9"] < last["ema15"] < last["ema200"]:
        return "DOWN"
    return "SIDE"


# ================= SAFE SWING =================
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


# ================= SAFE PREV DAY =================
def prev_day(df):
    if df.empty:
        return 0
    if len(df) < 24:
        return df["close"].iloc[-1]
    return df["close"].iloc[-24]


# ================= PULLBACK =================
def advanced_pullback(df):
    if df.empty or len(df) < 1:
        return None, None

    curr = df.iloc[-1]

    body = abs(curr["close"] - curr["open"])
    lower_wick = curr["open"] - curr["low"] if curr["close"] > curr["open"] else curr["close"] - curr["low"]
    upper_wick = curr["high"] - curr["close"] if curr["close"] > curr["open"] else curr["high"] - curr["open"]

    if (
        curr["close"] > curr["ema200"] and
        curr["ema9"] > curr["ema15"] and
        curr["low"] <= curr["ema15"] and
        lower_wick > body * 1.5
    ):
        return "BUY (PB)", "green"

    elif (
        curr["close"] < curr["ema200"] and
        curr["ema9"] < curr["ema15"] and
        curr["high"] >= curr["ema15"] and
        upper_wick > body * 1.5
    ):
        return "SELL (PB)", "red"

    return None, None


# ================= STRATEGY =================
def strategy(symbol):

    df15 = apply_ema(get_data(symbol, "15m"))
    df1h = apply_ema(get_data(symbol, "1h"))
    df4h = apply_ema(get_data(symbol, "4h"))

    if df15.empty or df1h.empty or df4h.empty:
        return "NO DATA", "red", 0

    t15 = trend(df15)
    t1h = trend(df1h)
    t4h = trend(df4h)

    sw = swing(df15)
    pd_level = prev_day(df1h)

    price = df15.iloc[-1]["close"]

    pb_signal, pb_color = advanced_pullback(df15)
    if pb_signal:
        return pb_signal, pb_color, price

    if t15 == "UP" and t1h == "UP" and t4h == "UP" and sw == "HH" and price > pd_level:
        return "BUY", "green", price

    elif t15 == "DOWN" and t1h == "DOWN" and t4h == "DOWN" and sw == "LL" and price < pd_level:
        return "SELL", "red", price

    return "-", "white", price


# ================= DASHBOARD =================
@app.route("/")
def dashboard():

    interval = request.args.get("tf", "15m")

    rows = ""

    for sym in SYMBOLS:
        signal, color, price = strategy(sym)

        if signal == "NO DATA":
            rows += f"""
            <tr>
                <td>{sym}</td>
                <td>0</td>
                <td>0</td>
                <td style='color:red'>NO DATA</td>
            </tr>
            """
            continue

        df = get_data(sym, interval)
        last = df.iloc[-1]

        rows += f"""
        <tr>
            <td>{sym}</td>
            <td>{last["open"]:.2f}</td>
            <td>{last["close"]:.2f}</td>
            <td style='color:{color}'>{signal}</td>
        </tr>
        """

    return f"""
    <html>
    <head>
        <meta http-equiv="refresh" content="10">
    </head>
    <body style="background:black; color:white; font-family:Arial;">
        <h2>🚀 PRO Trading Dashboard</h2>
        <table border="1" cellpadding="10">
            <tr>
                <th>COIN</th>
                <th>OPEN</th>
                <th>CLOSE</th>
                <th>SIGNAL</th>
            </tr>
            {rows}
        </table>
    </body>
    </html>
    """


# ================= RUN =================
if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
