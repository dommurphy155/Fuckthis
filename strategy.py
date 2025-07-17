import pandas as pd
from trade_logic import get_trade_signal
from instrument_selector import CURRENCY_PAIRS

async def generate_signals(*args, **kwargs):
    # args[0] should be a dict of {pair: DataFrame}
    pairs_with_data = args[0] if args else {}
    signals = []
    for pair in CURRENCY_PAIRS:
        df = pairs_with_data.get(pair)
        if df is not None:
            signal = get_trade_signal(pair, df)
            if signal:
                signals.append(signal)
    return signals