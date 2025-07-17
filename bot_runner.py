import asyncio
import logging
import nest_asyncio
import signal
import sys
from telegram_bot import TelegramBot

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("bot_error.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

# Global cancellation flag
shutdown_event = asyncio.Event()

def handle_shutdown(signame):
    logging.warning(f"Received shutdown signal: {signame}. Stopping gracefully...")
    shutdown_event.set()

async def main():
    try:
        bot = TelegramBot()
        await bot.app.initialize()
        await bot.app.start()
        await bot.app.updater.start_polling()
        logging.info("Telegram bot polling started. System is live.")

        # Wait indefinitely unless shutdown triggered
        await shutdown_event.wait()

    except Exception as e:
        logging.exception("Fatal error in bot_runner:", exc_info=e)
    finally:
        try:
            await bot.app.updater.stop()
            await bot.app.stop()
            logging.info("Bot stopped cleanly.")
        except Exception as cleanup_err:
            logging.error(f"Error during bot shutdown: {cleanup_err}")

if __name__ == "__main__":
    nest_asyncio.apply()
    for signame in {"SIGINT", "SIGTERM"}:
        signal.signal(getattr(signal, signame), lambda s, f: handle_shutdown(signame))
    asyncio.run(main())
