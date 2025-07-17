import pandas as pd
import numpy as np

RSI_PERIOD = 14
EMA_FAST = 12
EMA_SLOW = 26
MACD_SIGNAL = 9

def calculate_indicators(df):
    df = df.copy()

    df['ema_fast'] = df['close'].ewm(span=EMA_FAST, adjust=False).mean()
    df['ema_slow'] = df['close'].ewm(span=EMA_SLOW, adjust=False).mean()
    df['macd'] = df['ema_fast'] - df['ema_slow']
    df['macd_signal'] = df['macd'].ewm(span=MACD_SIGNAL, adjust=False).mean()
    df['rsi'] = compute_rsi(df['close'], RSI_PERIOD)
    df['atr'] = compute_atr(df)
    df['trend'] = detect_trend(df)

    return df

def compute_rsi(series, period):
    delta = series.diff()
    gain = np.where(delta > 0, delta, 0)
    loss = np.where(delta < 0, -delta, 0)
    gain = pd.Series(gain).rolling(window=period).mean()
    loss = pd.Series(loss).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def compute_atr(df, period=14):
    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - df['close'].shift())
    low_close = np.abs(df['low'] - df['close'].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()
    return atr

def detect_trend(df):
    if df['ema_fast'].iloc[-1] > df['ema_slow'].iloc[-1]:
        return "up"
    elif df['ema_fast'].iloc[-1] < df['ema_slow'].iloc[-1]:
        return "down"
    return "sideways"

def get_trade_signal(pair, df):
    if df is None or len(df) < 30:
        return None

    df = calculate_indicators(df)
    rsi = df['rsi'].iloc[-1]
    macd = df['macd'].iloc[-1]
    macd_signal = df['macd_signal'].iloc[-1]
    trend = df['trend'].iloc[-1]
    close_price = df['close'].iloc[-1]

    signal = None
    confidence = 0

    if trend == "up" and macd > macd_signal and rsi < 70:
        signal = "buy"
        confidence += 1
    elif trend == "down" and macd < macd_signal and rsi > 30:
        signal = "sell"
        confidence += 1

    if rsi > 80 or rsi < 20:
        confidence -= 0.5

    if signal and confidence >= 0.5:
        return {
            "instrument": pair,
            "direction": signal,
            "confidence": round(confidence, 2),
            "price": close_price,
        }

    return None

def get_top_signal(pairs_with_data):
    best_signal = None
    best_score = 0

    for pair, df in pairs_with_data.items():
        signal = get_trade_signal(pair, df)
        if signal and signal["confidence"] > best_score:
            best_signal = signal
            best_score = signal["confidence"]

    return best_signal
 