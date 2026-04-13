import pandas as pd

def apply_indicators(df):
    if df.empty: return df
    # 1. 3-EMA Setup
    df["ema9"] = df["close"].ewm(span=9).mean()
    df["ema15"] = df["close"].ewm(span=15).mean()
    df["ema200"] = df["close"].ewm(span=200).mean()
    
    # 2. Previous Day Level (Last 24 candles for 1h or approx for others)
    df["prev_level"] = df["close"].shift(24) 
    return df

def check_trend(df):
    if df.empty or len(df) < 2: return "SIDEWAYS"
    
    # Candle Close Rule: हमेशा पिछली क्लोज्ड कैंडल (-2) चेक करें
    last = df.iloc[-2]
    
    # BUY TREND Logic
    if last['close'] > last['ema9'] > last['ema15'] > last['ema200']:
        return "STRONG_UP"
    elif last['close'] > last['ema9'] > last['ema15']:
        return "BULLS_TREND"
    elif last['close'] > last['ema9']:
        return "SCALP_BUY"
        
    # SELL TREND Logic
    if last['close'] < last['ema9'] < last['ema15'] < last['ema200']:
        return "STRONG_DOWN"
    elif last['close'] < last['ema9'] < last['ema15']:
        return "SELL_TREND"
    elif last['close'] < last['ema9']:
        return "SCALP_SELL"
        
    return "SIDEWAYS"

def check_swing(df):
    if len(df) < 5: return "NONE"
    # HH: High1 > High2 > High3
    if df['high'].iloc[-2] > df['high'].iloc[-3] > df['high'].iloc[-4]:
        return "HH"
    # LL: Low1 < Low2 < Low3
    if df['low'].iloc[-2] < df['low'].iloc[-3] < df['low'].iloc[-4]:
        return "LL"
    return "NONE"

def check_pullback(df):
    if len(df) < 5: return None, "white"
    last = df.iloc[-2]
    body = abs(last['close'] - last['open'])
    lower_wick = min(last['open'], last['close']) - last['low']
    upper_wick = last['high'] - max(last['open'], last['close'])

    # BUY Pullback: Price > EMA200, EMA9 > EMA15, Rejection at EMA9 or EMA15
    if last['close'] > last['ema200'] and last['ema9'] > last['ema15']:
        if (last['low'] <= last['ema15'] or last['low'] <= last['ema9']) and lower_wick > body * 1.5:
            return "BUY (PB)", "#00ff00"
            
    # SELL Pullback: Price < EMA200, EMA9 < EMA15, Rejection at EMA9 or EMA15
    if last['close'] < last['ema200'] and last['ema9'] < last['ema15']:
        if (last['high'] >= last['ema15'] or last['high'] >= last['ema9']) and upper_wick > body * 1.5:
            return "SELL (PB)", "#ff4444"
            
    return None, "white"

def get_final_signal(data_dict):
    """
    data_dict: {'5m': df, '15m': df, '1h': df, '4h': df}
    """
    # 1. Multi-Timeframe Confirmation
    trends = {tf: check_trend(df) for tf, df in data_dict.items()}
    
    # 2. Check HH/LL on 15m (Primary timeframe)
    swing = check_swing(data_dict['15m'])
    
    # 3. Previous Day Level Check
    last_15m = data_dict['15m'].iloc[-2]
    pd_status = "BULL" if last_15m['close'] > last_15m['prev_level'] else "BEAR"

    # ✅ FINAL BUY SIGNAL
    if (all("UP" in trends[tf] or "BULLS" in trends[tf] or "SCALP_BUY" in trends[tf] for tf in trends) and 
        swing == "HH" and pd_status == "BULL"):
        return "FINAL BUY 🚀", "#00ff00"

    # ❌ FINAL SELL SIGNAL
    if (all("DOWN" in trends[tf] or "SELL" in trends[tf] or "SCALP_SELL" in trends[tf] for tf in trends) and 
        swing == "LL" and pd_status == "BEAR"):
        return "FINAL SELL 💀", "#ff4444"
        
    # Check for Pullback if no final signal
    pb_sig, pb_col = check_pullback(data_dict['15m'])
    if pb_sig: return pb_sig, pb_col

    return "SIDEWAYS ➖", "gray"

