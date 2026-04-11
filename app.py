from flask import Flask, request
import requests
import pandas as pd

app = Flask(__name__)

SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT"]

# ================= MULTI API DATA =================
def get_data(symbol, interval):

    interval_map = {
        "15m": "15",
        "1h": "60",
        "4h": "240"
    }

    # ========= 1. BINANCE =========
    try:
        url = "https://api.binance.com/api/v3/klines"
        params = {"symbol": symbol, "interval": interval, "limit": 200}
        res = requests.get(url, params=params, timeout=3)
        data = res.json()

        if isinstance(data, list):
            df = pd.DataFrame(data, columns=[
                "time","open","high","low","close","volume",
                "ct","qav","nt","tbv","tqv","ignore"
            ])
            for col in ["open","high","low","close"]:
                df[col] = pd.to_numeric(df[col])
            return df
    except:
        pass

    # ========= 2. BYBIT =========
    try:
        url = "https://api.bybit.com/v5/market/kline"
        params = {
            "category": "linear",
            "symbol": symbol,
            "interval": interval_map.get(interval, "15"),
            "limit": 200
        }
        res = requests.get(url, params=params, timeout=3).json()

        data = res.get("result", {}).get("list", [])
        if data:
            df = pd.DataFrame(data, columns=["time","open","high","low","close","volume","turnover"])
            df = df[::-1]
            for col in ["open","high","low","close"]:
                df[col] = pd.to_numeric(df[col])
            return df
    except:
        pass

    # ========= 3. DELTA =========
    try:
        url = "https://api.delta.exchange/v2/history/candles"
        params = {
            "symbol": symbol.replace("USDT", ""),
            "resolution": interval_map.get(interval, "15"),
            "limit": 200
        }
        res = requests.get(url, params=params, timeout=3).json()

        data = res.get("result", [])
        if data:
            df = pd.DataFrame(data)
            df.rename(columns={
                "time":"time",
                "open":"open",
                "high":"high",
                "low":"low",
                "close":"close"
            }, inplace=True)

            for col in ["open","high","low","close"]:
                df[col] = pd.to_numeric(df[col])

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


# ================= PREV DAY =================
def prev_day(df):
    if df.empty:
        return 0
    if len(df) < 24:
        return df["close"].iloc[-1]
    return df["close"].iloc[-24]


# ================= PULLBACK =================
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

    rows = ""

    for sym in SYMBOLS:
        signal, color, price = strategy(sym)

        rows += f"""
        <tr>
            <td>{sym}</td>
            <td>{price:.2f}</td>
            <td style='color:{color}'>{signal}</td>
        </tr>
        """

    return f"""
    <html>
    <body style="background:black; color:white;">
        <h2>🔥 PRO Trading Bot (Multi API)</h2>
        <table border="1" cellpadding="10">
            <tr>
                <th>COIN</th>
                <th>PRICE</th>
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
