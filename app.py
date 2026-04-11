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


# ================= TREND =================
def trend(df):
    if df.empty or len(df) < 3:
        return "SIDE"

    last = df.iloc[-1]

    if last["close"] > last["ema9"] > last["ema15"] > last["ema200"]:
        return "UP"
    elif last["close"] < last["ema9"] < last["ema15"] < last["ema200"]:
        return "DOWN"
    return "SIDE"


# ================= SWING =================
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


# ================= PREVIOUS DAY =================
def prev_day(df):
    if df.empty:
        return 0
    if len(df) < 24:
        return df["close"].iloc[-1]
    return df["close"].iloc[-24]


# ================= 🔥 REAL PULLBACK =================
def advanced_pullback(df):
    if df.empty:
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
        return "-", "white", 0

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


# ================= CHART =================
def chart(symbol, interval):

    df = get_data(symbol, interval)

    if df.empty:
        return "<h3 style='color:white;'>No Data</h3>"

    fig = go.Figure(data=[go.Candlestick(
        open=df["open"],
        high=df["high"],
        low=df["low"],
        close=df["close"]
    )])

    current_price = df["close"].iloc[-1]

    fig.add_hline(
        y=current_price,
        line_dash="dash",
        annotation_text=f"Live: {current_price}",
        annotation_position="top right"
    )

    fig.update_layout(template="plotly_dark", height=600)

    return fig.to_html(full_html=False)


# ================= DASHBOARD =================
@app.route("/")
def dashboard():

    interval = request.args.get("tf", "15m")

    rows = ""

    for sym in SYMBOLS:
        signal, color, price = strategy(sym)

        df = get_data(sym, interval)

        if df.empty:
            continue

        last = df.iloc[-1]

        rows += f"""
        <tr>
            <td><a href="/chart?symbol={sym}&tf={interval}" target="_blank">{sym}</a></td>
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
        <div>
            <a href="/?tf=15m">15m</a> |
            <a href="/?tf=1h">1H</a> |
            <a href="/?tf=4h">4H</a>
        </div>
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


# ================= FULL CHART =================
@app.route("/chart")
def full_chart():
    symbol = request.args.get("symbol")
    interval = request.args.get("tf", "15m")

    chart_html = chart(symbol, interval)

    return f"""
    <html>
    <body style="background:black;">
        <h2 style="color:white;">{symbol} - {interval}</h2>
        {chart_html}
    </body>
    </html>
    """


# ================= RUN =================
if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
