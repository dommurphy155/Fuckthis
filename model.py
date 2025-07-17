from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from telegram import Update
import asyncio

TOKEN = '7874560450:AAH-Bmu1GJTVjwRM7jounms9FFYfC4EbVBQ'
CHAT_ID = '8038953791'

class TelegramBot:
    """Manages Telegram integration for bot control and notifications."""
    def __init__(self):
        self.application = ApplicationBuilder().token(TOKEN).build()
        self.application.add_handler(CommandHandler('daily', self.daily))
        self.application.add_handler(CommandHandler('weekly', self.weekly))
        self.application.add_handler(CommandHandler('maketrade', self.maketrade))
        self.application.add_handler(CommandHandler('status', self.status))
        self.trading_engine = None  # Will be set by TradingEngine

    async def start(self):
        """Start the Telegram bot polling."""
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()

    async def send_message(self, text):
        """Send a message to the authorized chat."""
        await self.application.bot.send_message(chat_id=CHAT_ID, text=text)

    async def daily(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /daily command to report daily performance."""
        if str(update.message.chat_id) != CHAT_ID:
            await update.message.reply_text("Unauthorized.")
            return
        today_pl, open_trades, closed_trades = await self.trading_engine.get_daily_summary()
        usd_gbp = await self.trading_engine.get_usd_gbp_rate()
        message = (
            f"Daily P/L: £{today_pl * usd_gbp:.2f}\n"
            f"Open Trades: {len(open_trades)}\n"
            f"Closed Trades: {len(closed_trades)}"
        )
        await update.message.reply_text(message)

    async def weekly(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /weekly command to report weekly performance."""
        if str(update.message.chat_id) != CHAT_ID:
            await update.message.reply_text("Unauthorized.")
            return
        weekly_pl, trade_count = await self.trading_engine.get_weekly_summary()
        usd_gbp = await self.trading_engine.get_usd_gbp_rate()
        message = f"Weekly P/L: £{weekly_pl * usd_gbp:.2f}\nTotal Trades: {trade_count}"
        await update.message.reply_text(message)

    async def maketrade(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /maketrade command to place a high-confidence trade."""
        if str(update.message.chat_id) != CHAT_ID:
            await update.message.reply_text("Unauthorized.")
            return
        result = await self.trading_engine.execute_manual_trade()
        await update.message.reply_text(result)

    async def status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command to check system health."""
        if str(update.message.chat_id) != CHAT_ID:
            await update.message.reply_text("Unauthorized.")
            return
        balance = self.trading_engine.oanda.get_balance()
        open_trades = len(self.trading_engine.oanda.get_open_trades()))
        message = f"System Status: Running\nBalance: ${balance:.2f}\nOpen Trades: {open_trades}"
        await update.message.reply_text(message)
 