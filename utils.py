import hashlib
import random

async def get_current_spread(instrument, *args, **kwargs):
    # Simulate fetching spread from broker or market data
    # In production, replace with real API call
    return round(random.uniform(0.2, 2.5), 2)

async def get_atr_value(instrument, *args, **kwargs):
    # Simulate ATR value; in production, fetch from historical data
    return round(random.uniform(10, 50), 2)

def get_signal_hash(signal, *args, **kwargs):
    # Create a unique hash for a signal dict
    s = str(sorted(signal.items()))
    return hashlib.sha256(s.encode()).hexdigest()