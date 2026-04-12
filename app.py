from flask import Flask
import requests
import pandas as pd
import plotly.graph_objs as go
from datetime import datetime
import yfinance as yf

app = Flask(__name__)

# ================= SYMBOLS =================
CRYPTO_SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT"]
INDIAN_SYMBOLS = ["RELIANCE.NS","TCS.NS","HDFCBANK.NS"]

HEADERS = {"User-Agent": "Mozilla/5.0"}

# ================= CRYPTO DATA (ALL APIs) =================
def get_crypto_data(symbol, interval):

    interval_map = {"15m":"15","1h":"60","4h":"240"}

    # BINANCE
    try:
        r = requests.get("https://api.binance.com/api/v3/klines",
        params={"symbol":symbol,"interval":interval,"limit":200},
        headers=HEADERS,timeout=5)
        data = r.json()
        if isinstance(data,list) and len(data)>0:
            df = pd.DataFrame(data, columns=[
                "time","open","high","low","close","v","a","b","c","d","e","f"
            ])
            df = df[["time","open","high","low","close"]]
            df[["open","high","low","close"]] = df[["open","high","low","close"]].astype(float)
            df["time"] = pd.to_datetime(df["time"],unit="ms")
            print(symbol,"BINANCE ✅")
            return df
    except: pass

    # BYBIT
    try:
        r = requests.get("https://api.bybit.com/v5/market/kline",
        params={"category":"linear","symbol":symbol,"interval":interval_map[interval]},
        timeout=5)
        data = r.json().get("result",{}).get("list",[])
        if data:
            df = pd.DataFrame(data, columns=["time","open","high","low","close","v","t"])
            df = df[::-1]
            df[["open","high","low","close"]] = df[["open","high","low","close"]].astype(float)
            df["time"] = pd.to_datetime(df["time"].astype(float),unit="ms")
            print(symbol,"BYBIT ✅")
            return df
    except: pass

    # OKX
    try:
        r = requests.get("https://www.okx.com/api/v5/market/candles",
        params={"instId":symbol.replace("USDT","-USDT"),"bar":interval},
        timeout=5)
        data = r.json().get("data",[])
        if data:
            df = pd.DataFrame(data, columns=["time","open","high","low","close","a","b","c","d"])
            df = df[::-1]
            df[["open","high","low","close"]] = df[["open","high","low","close"]].astype(float)
            df["time"] = pd.to_datetime(df["time"].astype(float),unit="ms")
            print(symbol,"OKX ✅")
            return df
    except: pass

    # KUCOIN
    try:
        r = requests.get("https://api.kucoin.com/api/v1/market/candles",
        params={"symbol":symbol.replace("USDT","-USDT"),"type":interval},
        timeout=5)
        data = r.json().get("data",[])
        if data:
            df = pd.DataFrame(data, columns=["time","open","close","high","low","v","t"])
            df = df[::-1]
            df = df[["time","open","high","low","close"]]
            df[["open","high","low","close"]] = df[["open","high","low","close"]].astype(float)
            df["time"] = pd.to_datetime(df["time"].astype(float),unit="s")
            print(symbol,"KUCOIN ✅")
            return df
    except: pass

    print(symbol,"ALL FAIL ❌")
    return pd.DataFrame()

# ================= INDIAN DATA (4 API ADDED) =================
def get_indian_data(symbol):

    # 1. YAHOO
    try:
        df = yf.download(symbol, period="5d", interval="15m", progress=False)
        if not df.empty:
            df = df.rename(columns={"Open":"open","High":"high","Low":"low","Close":"close"})
            print(symbol,"YAHOO ✅")
            return df[["open","high","low","close"]]
    except: pass

    # 2. NSE
    try:
        url = f"https://www.nseindia.com/api/chart-databyindex?index={symbol.replace('.NS','')}"
        headers = {"User-Agent":"Mozilla/5.0"}
        s = requests.Session()
        s.get("https://www.nseindia.com",headers=headers)
        res = s.get(url,headers=headers,timeout=5)
        data = res.json().get("grapthData",[])
        if data:
            df = pd.DataFrame(data, columns=["time","price"])
            df["open"]=df["price"]
            df["high"]=df["price"]
            df["low"]=df["price"]
            df["close"]=df["price"]
            print(symbol,"NSE ✅")
            return df[["open","high","low","close"]]
    except: pass

    # 3. ALPHA
    try:
        url = f"https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY&symbol={symbol.replace('.NS','.BSE')}&interval=15min&apikey=demo"
        data = requests.get(url,timeout=5).json().get("Time Series (15min)",{})
        if data:
            df = pd.DataFrame(data).T.astype(float)
            df.columns=["open","high","low","close","v"]
            print(symbol,"ALPHA ✅")
            return df[["open","high","low","close"]]
    except: pass

    # 4. TWELVE DATA
    try:
        url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval=15min&apikey=demo"
        data = requests.get(url,timeout=5).json().get("values",[])
        if data:
            df = pd.DataFrame(data).astype(float)
            print(symbol,"TWELVE ✅")
            return df[["open","high","low","close"]]
    except: pass

    print(symbol,"ALL FAIL ❌")
    return pd.DataFrame()

# ================= EMA =================
def apply_ema(df):
    if df.empty: return df
    df["ema9"]=df["close"].ewm(span=9).mean()
    df["ema15"]=df["close"].ewm(span=15).mean()
    df["ema200"]=df["close"].ewm(span=200).mean()
    return df

# ================= STRATEGY (SAME) =================
def trend(df):
    if df.empty or len(df)<3: return "SIDE"
    last=df.iloc[-1]
    if last["close"]>last["ema9"]>last["ema15"]>last["ema200"]: return "UP"
    elif last["close"]<last["ema9"]<last["ema15"]<last["ema200"]: return "DOWN"
    return "SIDE"

def swing(df):
    if df.empty or len(df)<3: return "NONE"
    if df["high"].iloc[-1]>df["high"].iloc[-2]>df["high"].iloc[-3]: return "HH"
    elif df["low"].iloc[-1]<df["low"].iloc[-2]<df["low"].iloc[-3]: return "LL"
    return "NONE"

def prev_day(df):
    if df.empty: return 0
    return df["close"].iloc[-24] if len(df)>=24 else df["close"].iloc[-1]

def advanced_pullback(df):
    if df.empty: return None,None
    curr=df.iloc[-1]
    body=abs(curr["close"]-curr["open"])
    lw=curr["open"]-curr["low"]
    uw=curr["high"]-curr["close"]

    if curr["close"]>curr["ema200"] and curr["ema9"]>curr["ema15"] and lw>body*1.5:
        return "BUY (PB)","green"
    elif curr["close"]<curr["ema200"] and curr["ema9"]<curr["ema15"] and uw>body*1.5:
        return "SELL (PB)","red"

    return None,None

# ================= STRATEGY =================
def run_strategy(df):
    if df.empty: return "NO DATA","red",0,0,0,0

    # candle close fix
    if "time" in df.columns:
        if (datetime.utcnow() - df.iloc[-1]["time"]).seconds < 60:
            df=df.iloc[:-1]

    df=apply_ema(df)

    last=df.iloc[-1]
    o,h,l,c=last["open"],last["high"],last["low"],last["close"]

    pb,color=advanced_pullback(df)
    if pb: return pb,color,o,h,l,c

    t=trend(df)
    sw=swing(df)
    pdl=prev_day(df)

    if t=="UP" and sw=="HH" and c>pdl:
        return "BUY","green",o,h,l,c
    elif t=="DOWN" and sw=="LL" and c<pdl:
        return "SELL","red",o,h,l,c

    return "-","white",o,h,l,c

# ================= UI =================
@app.route("/")
def dashboard():

    crypto_rows=""
    for s in CRYPTO_SYMBOLS:
        sig,col,o,h,l,c=run_strategy(get_crypto_data(s,"15m"))
        crypto_rows+=f"<tr><td>{s}</td><td>O:{o:.2f} H:{h:.2f} L:{l:.2f} C:{c:.2f}</td><td style='color:{col}'>{sig}</td></tr>"

    india_rows=""
    for s in INDIAN_SYMBOLS:
        sig,col,o,h,l,c=run_strategy(get_indian_data(s))
        india_rows+=f"<tr><td>{s}</td><td>O:{o:.2f} H:{h:.2f} L:{l:.2f} C:{c:.2f}</td><td style='color:{col}'>{sig}</td></tr>"

    return f"""
    <html>
    <head><meta http-equiv="refresh" content="15"></head>
    <body style="background:#0e1117;color:white;font-family:sans-serif">

    <h2>🚀 CRYPTO MARKET</h2>
    <table border="1" cellpadding="10">
    <tr><th>COIN</th><th>OHLC</th><th>SIGNAL</th></tr>
    {crypto_rows}
    </table>

    <h2>🇮🇳 INDIAN MARKET</h2>
    <table border="1" cellpadding="10">
    <tr><th>STOCK</th><th>OHLC</th><th>SIGNAL</th></tr>
    {india_rows}
    </table>

    </body></html>
    """

if __name__ == "__main__":
    import os
    port=int(os.environ.get("PORT",10000))
    app.run(host="0.0.0.0",port=port)
