from typing import List
import random
import logging
from datetime import datetime
import pytz

CURRENCY_PAIRS = [
    "EUR_USD", "GBP_USD", "USD_JPY", "AUD_USD", "USD_CAD"
]

LOW_LIQUIDITY_HOURS = {
    "start": 21,
    "end": 23
}

def is_active_session_now() -> bool:
    """Determine if the current UTC time falls within any active session period.
    Returns:
        - bool: True if the current UTC time is within any predefined active session period, otherwise False.
    Processing Logic:
        - Retrieves the current UTC time and extracts the hour component.
        - Checks if the hour falls within one of the specified active session intervals."""
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
    # Only return the required trading pairs
    return CURRENCY_PAIRS
