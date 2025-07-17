from typing import List
import random
import logging
from datetime import datetime
import pytz

CURRENCY_PAIRS = [
    "EUR_USD", "GBP_USD", "USD_JPY", "AUD_USD", "USD_CHF"
]

LOW_LIQUIDITY_HOURS = {
    "start": 21,
    "end": 23
}

def is_active_session_now() -> bool:
    utc_now = datetime.utcnow().replace(tzinfo=pytz.utc)
    hour = utc_now.hour
    return (
        (7 <= hour < 16) or
        (13 <= hour < 22) or
        (0 <= hour < 9)
    )

def is_low_liquidity_period() -> bool:
    hour = datetime.utcnow().hour
    return LOW_LIQUIDITY_HOURS["start"] <= hour <= LOW_LIQUIDITY_HOURS["end"]

async def select_instruments() -> List[str]:
    # Stub: Replace with real instrument selection logic
    return CURRENCY_PAIRS
