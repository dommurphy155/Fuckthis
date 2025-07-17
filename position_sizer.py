from typing import Any
import asyncio

async def calculate_position_size(instrument, account_summary, atr, risk_per_trade=0.02):
    # Calculate position size based on 2% risk and ATR
    """Calculate the position size for a given trading instrument based on risk and ATR (Average True Range).
    Parameters:
        - instrument (str): The trading instrument, e.g., 'EURUSD', 'USDJPY'.
        - account_summary (dict): Dictionary containing account details, must include 'balance' key.
        - atr (float): The Average True Range in pips, used to determine stop loss distance.
        - risk_per_trade (float, optional): The fraction of account balance to risk per trade, defaults to 0.02 (2%).
    Returns:
        - int: The calculated number of units (position size) that should be traded.
    Processing Logic:
        - Balance is extracted from the account summary and multiplied by the risk factor to get the risk amount.
        - The pip value is adjusted based on whether the instrument contains 'JPY'.
        - The function calculates the units to be traded based on risk amount, ATR in pips, and pip value.
        - Ensures a minimum of 1 unit is returned to avoid trades with zero units."""
    balance = float(account_summary.get('balance', 0))
    risk_amount = balance * risk_per_trade
    # Assume pip value and ATR in pips for simplicity
    pip_value = 0.0001 if 'JPY' not in instrument else 0.01
    stop_loss_pips = atr if atr else 20
    units = int(risk_amount / (stop_loss_pips * pip_value))
    return max(units, 1)

class PositionSizer:
    """
    PositionSizer class calculates the size of a trading position based on risk management principles.
    Parameters:
        - risk_percentage (float): The percentage of the account balance to risk on a single trade.
        - account_balance (float): The total amount of money available in the account.
    Processing Logic:
        - Calculates the dollar amount to risk based on the account balance and risk percentage.
        - Computes the position size in terms of units using the stop loss in pips and pip value.
        - Ensures that the returned position size is at least one unit.
    """
    def __init__(self, risk_percentage: float, account_balance: float):
        self.risk_percentage = risk_percentage
        self.account_balance = account_balance

    async def calculate_position_size(self, stop_loss_pips: float, pip_value: float = 0.0001, instrument: str = "GBP_USD") -> int:
        risk_amount = self.account_balance * self.risk_percentage
        units = int(risk_amount / (stop_loss_pips * pip_value))
        return max(units, 1)
