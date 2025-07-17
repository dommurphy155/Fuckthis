import asyncio
from instrument_selector import select_instruments
from strategy import generate_signals
from trade_executor import execute_trade
from state_manager import StateManager
from oanda_client import get_account_summary
from telegram_bot import send_update
from logger import log_info
from datetime import datetime
from typing import Any

SCAN_INTERVAL = 60  # seconds

def get_next_trade_time(*args: Any, **kwargs: Any) -> str:
    return "N/A"

def get_last_signal_breakdown(*args: Any, **kwargs: Any) -> str:
    return "No breakdown available."

async def trading_loop():
    state_manager = StateManager()
    state_manager.load_state()
    last_reset_day = datetime.utcnow().day

    while True:
        try:
            current_day = datetime.utcnow().day
            if current_day != last_reset_day:
                state = state_manager.get_all()
                state["daily_trades"] = 0
                state["daily_profit"] = 0.0
                state["daily_loss"] = 0.0
                last_reset_day = current_day
                await log_info("✅ Daily counters reset.")

            instruments = await select_instruments()
            account_summary = await get_account_summary()
            signals = await generate_signals(instruments)

            if not signals:
                await log_info("📭 No signals generated.")
            else:
                best_signal = signals[0]
                result = await execute_trade(best_signal, account_summary, state_manager.get_all())
                await send_update(result)
                await log_info(result)

            state_manager.save()

        except Exception as e:
            await log_info(f"❌ Trading loop error: {e}")

        await asyncio.sleep(SCAN_INTERVAL)

if __name__ == "__main__":
    asyncio.run(trading_loop())
 