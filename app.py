from flask import Flask
import requests
import pandas as pd
import plotly.graph_objs as go

app = Flask(__name__)

# ===== SYMBOLS =====
CRYPTO_SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT"]
INDIAN_SYMBOLS = ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS"]

HEADERS = {"User-Agent": "Mozilla/5.0"}

# ================= DATA FETCH =================
def get_crypto_data(symbol, interval):
    try:
        url = "https://api.binance.com/api/v3/klines"
        params = {"symbol": symbol, "interval": interval, "limit": 200}
        res = requests.get(url, params=params, timeout=10, headers=HEADERS)

        if res.status_code == 200:
            data = res.json()

            if isinstance(data, list):
                df = pd.DataFrame(data, columns=[
                    "time","open","high","low","close","volume",
                    "ct","qav","nt","tbv","tqv","ignore"
                ])

                for col in ["open","high","low","close"]:
                    df[col] = pd.to_numeric(df[col], errors="coerce")

                df.dropna(inplace=True)
                return df
    except:
        pass

    return pd.DataFrame()


# ===== INDIAN MARKET (FREE API) =====
def get_indian_data(symbol):
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
        res = requests.get(url, headers=HEADERS).json()

        result = res["chart"]["result"][0]
        quotes = result["indicators"]["quote"][0]

        df = pd.DataFrame({
            "open": quotes["open"],
            "high": quotes["high"],
            "low": quotes["low"],
            "close": quotes["close"]
        })

        df.dropna(inplace=True)
        return df
    except:
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
    if len(df) < 24:
        return df["close"].iloc[-1]
    return df["close"].iloc[-24]


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


def strategy(df):
    if df.empty:
        return "NO DATA", "red", 0

    df = apply_ema(df)

    t = trend(df)
    sw = swing(df)
    price = df.iloc[-1]["close"]

    pb_signal, pb_color = advanced_pullback(df)
    if pb_signal:
        return pb_signal, pb_color, price

    if t == "UP" and sw == "HH":
        return "BUY", "green", price
    elif t == "DOWN" and sw == "LL":
        return "SELL", "red", price

    return "-", "white", price


# ================= CHART =================
def get_chart():
    df = apply_ema(get_crypto_data("BTCUSDT", "15m"))

    if df.empty:
        return "<h3>No Chart Data</h3>"

    fig = go.Figure()

    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df['open'],
        high=df['high'],
        low=df['low'],
        close=df['close']
    ))

    fig.add_trace(go.Scatter(x=df.index, y=df['ema9'], name="EMA 9"))
    fig.add_trace(go.Scatter(x=df.index, y=df['ema15'], name="EMA 15"))
    fig.add_trace(go.Scatter(x=df.index, y=df['ema200'], name="EMA 200"))

    fig.update_layout(template="plotly_dark", height=500)

    return fig.to_html(full_html=False)


# ================= DASHBOARD =================
@app.route("/")
def dashboard():

    crypto_rows = ""
    for sym in CRYPTO_SYMBOLS:
        df = get_crypto_data(sym, "15m")
        signal, color, price = strategy(df)

        crypto_rows += f"""
        <tr>
            <td>{sym}</td>
            <td>{price:.2f}</td>
            <td style='color:{color}'>{signal}</td>
        </tr>
        """

    indian_rows = ""
    for sym in INDIAN_SYMBOLS:
        df = get_indian_data(sym)
        signal, color, price = strategy(df)

        indian_rows += f"""
        <tr>
            <td>{sym}</td>
            <td>{price:.2f}</td>
            <td style='color:{color}'>{signal}</td>
        </tr>
        """

    chart = get_chart()

    return f"""
    <html>
    <head>
        <meta http-equiv="refresh" content="10">
    </head>

    <body style="background:#0e1117; color:white; font-family:sans-serif;">

        <h2>🚀 Trading Dashboard PRO (Crypto + Indian Market)</h2>

        <div style="display:flex; gap:20px;">

            <div style="width:30%;">

                <h3>Crypto</h3>
                <table border="1" cellpadding="10">
                    <tr><th>COIN</th><th>PRICE</th><th>SIGNAL</th></tr>
                    {crypto_rows}
                </table>

                <h3>Indian Market</h3>
                <table border="1" cellpadding="10">
                    <tr><th>STOCK</th><th>PRICE</th><th>SIGNAL</th></tr>
                    {indian_rows}
                </table>

            </div>

            <div style="width:70%;">
                {chart}
            </div>

        </div>

    </body>
    </html>
    """


# ================= RUN =================
if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
