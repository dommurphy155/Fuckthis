import asyncio
import logging
import os
import platform
import psutil
import time
import aiofiles
import socket
from datetime import datetime
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters
)
from trade_executor import execute_trade
from trade_closer import close_all_trades
from trading_bot import get_next_trade_time, get_last_signal_breakdown
from state_manager import StateManager
from oanda_client import get_open_positions, get_account_summary
from config import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, MAX_COMMANDS_PER_MIN

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def send_update(*args, **kwargs) -> None:
    pass  # Placeholder for any future broadcast messages

class TelegramBot:
    """Initialize a Telegram bot with predefined command handlers and a message handler to manage interactions.
    Parameters:
        - None
    Returns:
        - None
    Processing Logic:
        - Initializes an empty list 'command_timestamps' to store the timestamps of received commands.
        - Configures the 'Application' instance with a unique 'TELEGRAM_TOKEN' that establishes authentication with the Telegram API.
        - Adds various 'CommandHandler' instances to manage specific bot commands: "status", "report", "maketrade", "closetrades", "diagnostics", and "whatyoudoin".
        - Utilizes a 'MessageHandler' to restrict chats that contain text but are not commands."""
    def __init__(self):
        """Initialize a Telegram bot with predefined command handlers and a message handler to manage interactions.
        Parameters:
            None
        Returns:
            None
        Processing Logic:
            - Initializes an empty list 'command_timestamps' to store the timestamps of received commands.
            - Configures the 'Application' instance with a unique 'TELEGRAM_TOKEN' that establishes authentication with the Telegram API.
            - Adds various 'CommandHandler' instances to manage specific bot commands: "status", "report", "maketrade", "closetrades", "diagnostics", and "whatyoudoin".
            - Utilizes a 'MessageHandler' to restrict chats that contain text but are not commands."""
        self.command_timestamps = []
        self.app = Application.builder().token(TELEGRAM_TOKEN).build()
        self.app.add_handler(CommandHandler("status", self.status))
        self.app.add_handler(CommandHandler("report", self.report))
        self.app.add_handler(CommandHandler("maketrade", self.maketrade))
        self.app.add_handler(CommandHandler("closetrades", self.closetrades))
        self.app.add_handler(CommandHandler("diagnostics", self.diagnostics))
        self.app.add_handler(CommandHandler("whatyoudoin", self.whatyoudoin))
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.restrict_chat))

    def rate_limited(self):
        now = time.time()
        self.command_timestamps = [t for t in self.command_timestamps if now - t < 60]
        if len(self.command_timestamps) >= MAX_COMMANDS_PER_MIN:
            return True
        self.command_timestamps.append(now)
        return False

    async def restrict_chat(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat = update.effective_chat
        if chat is None or str(chat.id) != TELEGRAM_CHAT_ID:
            if update.message:
                await update.message.reply_text("Unauthorized.")
            return

    async def status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send a message in Telegram chat with system status details.
        Parameters:
            - update (Update): Incoming update containing message and chat information.
            - context (ContextTypes.DEFAULT_TYPE): Context object providing contextual information such as bot data and user data.
        Returns:
            - None: The function does not return any value; it performs an action by sending a message in the specified chat.
        Processing Logic:
            - Checks for rate limiting before proceeding.
            - Ensures the message is sent only in the specified TELEGRAM_CHAT_ID.
            - Retrieves and formats CPU, RAM, system uptime, next trade time, and Telegram connection latency.
            - Sends a formatted status message using markdown in the designated Telegram chat."""
        if self.rate_limited():
            return
        chat = update.effective_chat
        if chat is None or str(chat.id) != TELEGRAM_CHAT_ID:
            return
        if update.message is None:
            return
        cpu = psutil.cpu_percent()
        ram = psutil.virtual_memory().percent
        uptime = time.time() - psutil.boot_time()
        next_trade_time = get_next_trade_time()
        latency = await self.ping_latency()
        msg = (
            f"🖥️ *System Status*\n"
            f"• CPU: {cpu}%\n"
            f"• RAM: {ram}%\n"
            f"• Uptime: {int(uptime // 3600)}h {(uptime % 3600) // 60:.0f}m\n"
            f"• Next trade: `{next_trade_time}`\n"
            f"• Telegram latency: `{latency:.2f} ms`"
        )
        await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)

    async def report(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Generate and send a trading report in response to a Telegram update.
        Parameters:
            - update (Update): Represents an incoming Telegram update.
            - context (ContextTypes.DEFAULT_TYPE): Contains metadata and helpers related to a Telegram bot's operation.
        Returns:
            - None: The function does not return any value, but replies to the update with a formatted trading report message.
        Processing Logic:
            - If the request is rate-limited or the update is not from the specified chat, the function exits without processing.
            - Retrieves trading state data to calculate total profit/loss, win rate, trades executed today, and number of open positions.
            - Constructs a formatted report as a message string using Markdown for styling.
            - Sends the trade report as a Telegram message reply, provided the message is valid and not empty."""
        if self.rate_limited():
            return
        chat = update.effective_chat
        if chat is None or str(chat.id) != TELEGRAM_CHAT_ID:
            return
        if update.message is None:
            return
        state_manager = StateManager()
        state_manager.load_state()
        state = state_manager.get_all()
        positions = await get_open_positions()
        pnl = state.get("total_profit_loss", 0)
        wins = state.get("win_count", 0)
        losses = state.get("loss_count", 0)
        trades_today = state.get("trades_today", 0)
        win_rate = (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0
        msg = (
            f"📊 *Trade Report*\n"
            f"• Balance P&L: £{pnl:.2f}\n"
            f"• Win Rate: {win_rate:.2f}%\n"
            f"• Trades Today: {trades_today}\n"
            f"• Open Positions: {len(positions)}"
        )
        await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)

    async def maketrade(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Initiates a manual trade based on specific conditions and responds with the trade result.
        Parameters:
            - update (Update): Represents an incoming update from Telegram, containing details of the chat and message.
            - context (ContextTypes.DEFAULT_TYPE): Provides the context in which this function is being called, including bot and user data.
        Returns:
            - None
        Processing Logic:
            - Checks if the user is rate-limited before proceeding.
            - Verifies the chat ID is authorized to initiate trades.
            - Ensures a message is present to respond to before executing the trade.
            - Executes the trade asynchronously and sends a reply with the result formatted using Markdown."""
        if self.rate_limited():
            return
        chat = update.effective_chat
        if chat is None or str(chat.id) != TELEGRAM_CHAT_ID:
            return
        if update.message is None:
            return
        result = await execute_trade()
        await update.message.reply_text(f"📈 Manual Trade: `{result}`", parse_mode=ParseMode.MARKDOWN)

    async def closetrades(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Close all active trades based on a telegram update command.
        Parameters:
            - update (Update): The telegram update object containing the information needed to process the command.
            - context (ContextTypes.DEFAULT_TYPE): The context in which the command is executed.
        Returns:
            - None: The function sends a reply in the telegram chat and doesn't return any value.
        Processing Logic:
            - Checks if the function execution is rate-limited before proceeding with trade closure.
            - Verifies if the command is received in the correct chat by comparing chat ID.
            - Calls 'close_all_trades()' to initiate trade closure and responds with the result of the closure."""
        if self.rate_limited():
            return
        chat = update.effective_chat
        if chat is None or str(chat.id) != TELEGRAM_CHAT_ID:
            return
        if update.message is None:
            return
        result = await close_all_trades()
        await update.message.reply_text(f"❌ Closed Trades: `{result}`", parse_mode=ParseMode.MARKDOWN)

    async def diagnostics(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Provides diagnostic information regarding recent operational errors.
        Parameters:
            - update (Update): Represents incoming update information including chat and message data.
            - context (ContextTypes.DEFAULT_TYPE): Provides contextual information such as bot data and job queues.
        Returns:
            - None: This function does not return a value but sends a message in response to the diagnostics request.
        Processing Logic:
            - Checks if the bot is rate-limited before proceeding; if rate-limited, exits the function.
            - Validates that the chat ID matches the specified TELEGRAM_CHAT_ID before continuing.
            - Retrieves recent error data using the get_last_errors method and replies to the user with this information formatted in Markdown."""
        if self.rate_limited():
            return
        chat = update.effective_chat
        if chat is None or str(chat.id) != TELEGRAM_CHAT_ID:
            return
        if update.message is None:
            return
        diagnostics_text = await self.get_last_errors()
        await update.message.reply_text(f"🛠️ *Diagnostics*\n```\n{diagnostics_text}\n```", parse_mode=ParseMode.MARKDOWN)

    async def whatyoudoin(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Respond with the latest decision breakdown via Telegram message.
        Parameters:
            - update (Update): Represents an incoming update in the chat.
            - context (ContextTypes.DEFAULT_TYPE): Passes context related to the current update.
        Returns:
            - None: No return value. The function sends a message if conditions are met.
        Processing Logic:
            - Halts if rate limiting conditions are active.
            - Checks if the chat ID matches a predefined ID to ensure messages are sent in the correct chat.
            - Retrieves the last signal breakdown using `get_last_signal_breakdown`."""
        if self.rate_limited():
            return
        chat = update.effective_chat
        if chat is None or str(chat.id) != TELEGRAM_CHAT_ID:
            return
        if update.message is None:
            return
        breakdown = get_last_signal_breakdown()
        await update.message.reply_text(f"🤖 *Decision Breakdown*\n```\n{breakdown}\n```", parse_mode=ParseMode.MARKDOWN)

    async def ping_latency(self):
        """Measure the latency to the Telegram API server.
        Parameters:
            None
        Returns:
            - float: The round-trip latency in milliseconds to "api.telegram.org".
            - int: Returns -1 in case of an exception, indicating failure to connect.
        Processing Logic:
            - Uses asyncio to asynchronously open and close a connection.
            - Calculates latency by measuring the time taken to establish and close the connection."""
        try:
            start = time.time()
            reader, writer = await asyncio.open_connection("api.telegram.org", 443)
            writer.close()
            await writer.wait_closed()
            return (time.time() - start) * 1000
        except Exception:
            return -1

    async def get_last_errors(self):
        try:
            async with aiofiles.open("bot_error.log", "r") as f:
                lines = await f.readlines()
            return "".join(lines[-10:]) if lines else "No recent errors."
        except FileNotFoundError:
            return "Error log not found."
 