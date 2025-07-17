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
    def __init__(self):
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
 