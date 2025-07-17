import asyncio
from oanda_client import OandaClient
from position_sizer import calculate_position_size
from logger import log_trade_action
from state_manager import record_open_trade, get_state, get_account_summary, load_state
from utils import get_current_spread, get_atr_value, get_signal_hash
from time import time

MAX_SPREAD_PIPS = 2.0
MAX_TRADES_PER_DAY = 10
MAX_GLOBAL_TRADES = 50
MIN_TIME_BETWEEN_TRADES_SEC = 6

trade_locks = {}

async def can_trade(instrument: str, state: dict) -> (bool, str):
    if len(state.get("open_trades", [])) >= MAX_GLOBAL_TRADES:
        return False, "Max global trades reached."

    if state.get("daily_trade_count", {}).get(instrument, 0) >= MAX_TRADES_PER_DAY:
        return False, f"Max trades for {instrument} today."

    last_time = state.get("last_trade_time", {}).get(instrument, 0)
    if time() - last_time < MIN_TIME_BETWEEN_TRADES_SEC:
        return False, f"Cooldown not passed for {instrument}."

    return True, ""

async def execute_trade(signal: dict, account_summary: dict, state: dict) -> str:
    instrument = signal["instrument"]
    direction = signal["direction"]
    spread = await get_current_spread(instrument)
    atr = await get_atr_value(instrument)

    if spread > MAX_SPREAD_PIPS:
        return f"Spread too high on {instrument} ({spread:.2f} pips)"

    can, reason = await can_trade(instrument, state)
    if not can:
        return reason

    if instrument in trade_locks:
        return f"Trade already in progress for {instrument}."

    trade_locks[instrument] = True
    client = OandaClient()

    try:
        signal_hash = get_signal_hash(signal)
        if signal_hash in state.get("recent_signals", []):
            return f"Duplicate signal skipped for {instrument}."

        size = await calculate_position_size(instrument, account_summary, atr)
        units = size if direction.lower() == "buy" else -size
        order_result = client.place_order(instrument, units)

        if order_result is None:
            return "Order failed: No response from broker."

        if order_result.get("errorMessage"):
            return f"Order failed: {order_result['errorMessage']}"

        trade_id = order_result.get("tradeOpened", {}).get("tradeID")
        if not trade_id:
            return "Order failed: No trade ID returned."

        await record_open_trade(trade_id, instrument, direction, size, atr)
        await log_trade_action(f"Executed {direction.upper()} on {instrument} for {size} units (ATR: {atr:.2f})")

        return f"Trade executed: {instrument} {direction} x{size}"
    except Exception as e:
        return f"Trade error: {e}"
    finally:
        trade_locks.pop(instrument, None)

# ✅ New for Telegram bot: safe one-off manual trade trigger
async def execute_single_trade(signal: dict) -> str:
    state = await load_state()
    account_summary = await get_account_summary()
    return await execute_trade(signal, account_summary, state)
 