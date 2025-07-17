import pandas as pd
import numpy as np

RSI_PERIOD = 14
EMA_FAST = 12
EMA_SLOW = 26
MACD_SIGNAL = 9

def calculate_indicators(df):
    """Calculates technical indicators for a given DataFrame containing stock data.
    Parameters:
        - df (pandas.DataFrame): DataFrame with at least a 'close' column containing closing prices for calculation.
    Returns:
        - pandas.DataFrame: DataFrame with additional columns for each calculated technical indicator.
    Processing Logic:
        - Copies the input DataFrame to prevent modification of the original data.
        - Calculates the exponential moving averages (EMA) with specified fast and slow periods.
        - Computes the Moving Average Convergence Divergence (MACD) and its signal line.
        - Utilizes auxiliary functions to calculate the Relative Strength Index (RSI) and Average True Range (ATR).
        - Detects trends using an external function and appends results to the DataFrame."""
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
    """Compute the Relative Strength Index (RSI) for a given series of data.
    Parameters:
        - series (pd.Series): A pandas Series representing the data for which RSI needs to be computed.
        - period (int): The number of observations used for calculating the rolling average of gains and losses.
    Returns:
        - pd.Series: A pandas Series representing the RSI values calculated over the input series data.
    Processing Logic:
        - Calculates the difference between consecutive data points to determine gains and losses.
        - Applies rolling mean to the gains and losses over the specified period to smooth them.
        - Computes the relative strength (RS) as the ratio of averaged gains to averaged losses."""
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
    """Determine the trade signal for a given currency pair based on technical indicators.
    Parameters:
        - pair (str): Currency pair identifier like 'EUR/USD'.
        - df (pd.DataFrame): DataFrame containing at least 30 rows of recent market data with necessary indicators.
    Returns:
        - dict or None: Dictionary containing trade signal information such as instrument, direction, confidence, and price, or None if conditions are not met.
    Processing Logic:
        - Calculates indicators such as RSI, MACD, MACD Signal, and trend from the DataFrame.
        - Generates 'buy' signal if the trend is up, MACD is greater than MACD Signal, and RSI is less than 70.
        - Generates 'sell' signal if the trend is down, MACD is less than MACD Signal, and RSI is greater than 30.
        - Adjusts confidence based on extreme RSI values."""
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
    """Determine the best trade signal based on confidence scores from multiple pairs.
    Parameters:
        - pairs_with_data (dict): A dictionary where keys are pair identifiers and values are dataframes containing relevant trading data.
    Returns:
        - dict or None: The trade signal with the highest confidence score, or None if no valid signals are found.
    Processing Logic:
        - Iterates through each trading pair in the dictionary to extract trade signals.
        - Identifies the signal with the highest 'confidence' attribute."""
    best_signal = None
    best_score = 0

    for pair, df in pairs_with_data.items():
        signal = get_trade_signal(pair, df)
        if signal and signal["confidence"] > best_score:
            best_signal = signal
            best_score = signal["confidence"]

    return best_signal
 