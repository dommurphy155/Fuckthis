import asyncio
from datetime import datetime, timedelta
import pytz
from oanda import OANDAClient
from telegram_bot import TelegramBot
from trading import TradingEngine
from database import Database
from logger import setup_logger

async def reset_daily_counters(trading_engine):
    """Reset daily trade counters at midnight UK time."""
    while True:
        now = datetime.now(pytz.timezone('Europe/London'))
        next_midnight = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        wait_seconds = (next_midnight - now).total_seconds()
        await asyncio.sleep(wait_seconds)
        trading_engine.reset_daily_counters()
        trading_engine.logger.info("Daily trade counters reset.")

async def main():
    """Initialize and run the Forex trading bot."""
    logger = setup_logger()
    db = Database()
    oanda = OANDAClient()
    telegram = TelegramBot()
    trading = TradingEngine(oanda, db, telegram, logger)

    # Sync open trades with database on startup
    await trading.sync_open_trades()

    # Define background tasks
    telegram_task = asyncio.create_task(telegram.start())
    trading_task = asyncio.create_task(trading.run_trading_loop())
    monitoring_task = asyncio.create_task(trading.monitor_trades())
    reset_task = asyncio.create_task(reset_daily_counters(trading))

    # Run all tasks concurrently
    await asyncio.gather(telegram_task, trading_task, monitoring_task, reset_task)

if __name__ == "__main__":
    asyncio.run(main())
 