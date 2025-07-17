from typing import Any
import asyncio

async def calculate_position_size(instrument, account_summary, atr, risk_per_trade=0.02):
    # Calculate position size based on 2% risk and ATR
    balance = float(account_summary.get('balance', 0))
    risk_amount = balance * risk_per_trade
    # Assume pip value and ATR in pips for simplicity
    pip_value = 0.0001 if 'JPY' not in instrument else 0.01
    stop_loss_pips = atr if atr else 20
    units = int(risk_amount / (stop_loss_pips * pip_value))
    return max(units, 1)

class PositionSizer:
    def __init__(self, risk_percentage: float, account_balance: float):
        self.risk_percentage = risk_percentage
        self.account_balance = account_balance

    async def calculate_position_size(self, stop_loss_pips: float, pip_value: float = 0.0001, instrument: str = "GBP_USD") -> int:
        risk_amount = self.account_balance * self.risk_percentage
        units = int(risk_amount / (stop_loss_pips * pip_value))
        return max(units, 1)
