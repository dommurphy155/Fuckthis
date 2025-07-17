import pandas as pd
from trade_logic import get_trade_signal
from instrument_selector import CURRENCY_PAIRS

async def generate_signals(*args, **kwargs):
    # args[0] should be a dict of {pair: DataFrame}
    """Generate trading signals for specified currency pairs based on provided data.
    Parameters:
        - *args: Positional arguments.
        - **kwargs: Keyword arguments.
    Returns:
        - list: A list of generated trade signals.
    Processing Logic:
        - The first positional argument is expected to be a dictionary pairing currency pairs with pandas DataFrames containing relevant data.
        - Iterates over a predefined list of currency pairs, checking if data is available for each.
        - Utilizes a helper function, `get_trade_signal`, to generate signals for pairs with available data."""
    pairs_with_data = args[0] if args else {}
    signals = []
    for pair in CURRENCY_PAIRS:
        df = pairs_with_data.get(pair)
        if df is not None:
            signal = get_trade_signal(pair, df)
            if signal:
                signals.append(signal)
    return signals