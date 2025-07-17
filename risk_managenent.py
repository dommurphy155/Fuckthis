class RiskManager:
    """Calculates position sizes and trade parameters."""
    def __init__(self, oanda):
        self.oanda = oanda

    def calculate_position_size(self, pair, entry_price, stop_loss):
        """Calculate units based on 1% risk per trade."""
        balance = self.oanda.get_balance()
        risk = balance * 0.01  # 1% risk
        sl_pips = abs(entry_price - stop_loss)
        pip_value = 0.0001 if 'JPY' not in pair else 0.01
        units = int((risk / (sl_pips * pip_value)) * 10000)
        return max(units, 1000)  # Minimum 1000 units

    def set_trade_levels(self, pair, entry_price, direction, atr):
        """Set stop loss and take profit levels."""
        sl_pips = atr * 2
        tp_pips = sl_pips * 1.5
        sl = entry_price - sl_pips if direction == 'long' else entry_price + sl_pips
        tp = entry_price + tp_pips if direction == 'long' else entry_price - tp_pips
        return sl, tp
 