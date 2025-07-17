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
    """Initialize and start a Telegram bot, handling shutdown events.
    Parameters:
        None
    Returns:
        None
    Processing Logic:
        - Initializes and starts the Telegram bot application.
        - Begins polling for updates to keep the bot active.
        - Handles exceptions during runtime and logs errors.
        - Ensures clean shutdown of bot resources when a shutdown event occurs."""
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
