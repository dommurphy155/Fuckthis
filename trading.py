import asyncio
import numpy as np
from datetime import datetime, timedelta
import pytz

# Import ta indicators directly
from ta.momentum import RSIIndicator, StochRSIIndicator, ROCIndicator
from ta.trend import MACD, ADXIndicator, EMAIndicator
from ta.volatility import AverageTrueRange, BollingerBands, KeltnerChannel
from ta.volume import OnBalanceVolumeIndicator
from ta.patterns import (  # Not all patterns in ta, so this might be limited
    # Patterns would require custom implementation if needed
)

class TradingEngine:
    """Manages trading logic, signal generation, and trade monitoring."""
    def __init__(self, oanda, db, telegram, logger):
        self.oanda = oanda
        self.db = db
        self.telegram = telegram
        self.logger = logger
        self.telegram.trading_engine = self
        self.model = TradingModel()
        self.pairs = ['EUR_USD', 'GBP_USD', 'USD_JPY', 'AUD_USD', 'USD_CAD', 'USD_CHF', 'NZD_USD']
        self.daily_trades = {pair: 0 for pair in self.pairs}
        self.max_trades_per_day = 5
        self.max_open_trades = 7

    async def sync_open_trades(self):
        """Sync database with current open trades from OANDA."""
        open_trades = self.oanda.get_open_trades()
        for trade in open_trades:
            self.db.update_trade(trade['trade_id'], status='open', entry_price=trade['entry_price'])

    async def get_usd_gbp_rate(self):
        """Fetch current USD/GBP exchange rate."""
        bid, ask = self.oanda.get_current_price('USD_GBP')
        return (bid + ask) / 2

    def compute_indicators(self, candles):
        """Compute technical indicators for 1m or 15m candles."""
        closes = np.array([float(c['close']) for c in candles])
        highs = np.array([float(c['high']) for c in candles])
        lows = np.array([float(c['low']) for c in candles])
        volumes = np.array([float(c['volume']) for c in candles])

        # RSI
        rsi = RSIIndicator(pd.Series(closes), window=14).rsi().iloc[-1]

        # MACD Histogram
        macd = MACD(pd.Series(closes))
        hist = macd.macd_diff().iloc[-1]

        # ADX
        adx = ADXIndicator(pd.Series(highs), pd.Series(lows), pd.Series(closes), window=14).adx().iloc[-1]

        # ATR
        atr = AverageTrueRange(pd.Series(highs), pd.Series(lows), pd.Series(closes), window=14).average_true_range().iloc[-1]

        # Bollinger Bands and %b
        bb = BollingerBands(pd.Series(closes), window=20)
        upper = bb.bollinger_hband().iloc[-1]
        middle = bb.bollinger_mavg().iloc[-1]
        lower = bb.bollinger_lband().iloc[-1]
        percent_b = (closes[-1] - lower) / (upper - lower)
        bb_width = (upper - lower) / middle

        # SAR — ta doesn't have SAR, fallback to 0 or implement later
        sar = 0

        # OBV
        obv = OnBalanceVolumeIndicator(pd.Series(closes), pd.Series(volumes)).on_balance_volume().iloc[-1]

        # EMA 20
        ema = EMAIndicator(pd.Series(closes), window=20).ema_indicator().iloc[-1]

        # Keltner Channel upper and lower
        kc = KeltnerChannel(pd.Series(highs), pd.Series(lows), pd.Series(closes), window=20)
        keltner_upper = kc.keltner_channel_hband().iloc[-1]
        keltner_lower = kc.keltner_channel_lband().iloc[-1]

        # Donchian Channel high and low — not in ta, approximate with rolling max/min
        donchian_high = pd.Series(highs).rolling(window=20).max().iloc[-1]
        donchian_low = pd.Series(lows).rolling(window=20).min().iloc[-1]

        return [
            rsi, hist, adx, atr, percent_b, bb_width, sar, obv,
            keltner_upper - keltner_lower, donchian_high - donchian_low
        ]

    async def generate_signals(self):
        """Generate trading signals for all pairs."""
        signals = {}
        for pair in self.pairs:
            candles_1m = self.oanda.get_candle_data(pair, 50, 'M1')
            candles_15m = self.oanda.get_candle_data(pair, 50, 'M15')
            features_1m = self.compute_indicators(candles_1m)
            features_15m = self.compute_indicators(candles_15m)
            features = features_1m + features_15m
            direction, confidence = self.model.predict(features)
            signals[pair] = (direction, confidence)
        return signals

    async def place_trade(self, pair, direction, confidence):
        """Place a trade with risk management."""
        bid, ask = self.oanda.get_current_price(pair)
        entry_price = ask if direction == 'long' else bid
        candles = self.oanda.get_candle_data(pair, 50, 'M15')
        highs = np.array([float(c['high']) for c in candles])
        lows = np.array([float(c['low']) for c in candles])
        closes = np.array([float(c['close']) for c in candles])
        atr = AverageTrueRange(pd.Series(highs), pd.Series(lows), pd.Series(closes), window=14).average_true_range().iloc[-1]
        sl_pips = atr * 2
        tp_pips = sl_pips * 1.5
        sl = entry_price - sl_pips if direction == 'long' else entry_price + sl_pips
        tp = entry_price + tp_pips if direction == 'long' else entry_price - tp_pips
        balance = self.oanda.get_balance()
        risk = balance * 0.01  # 1% risk per trade
        pip_value = 0.0001 if 'JPY' not in pair else 0.01
        units = int((risk / (sl_pips * pip_value)) * 10000)
        trade_id = self.oanda.place_trade(pair, units, direction, sl, tp)
        entry_time = datetime.now(pytz.utc)
        expected_profit = (abs(tp - entry_price) * units * pip_value) * await self.get_usd_gbp_rate()
        self.db.insert_trade(trade_id, pair, entry_time, confidence, expected_profit, sl, tp, units, entry_price)
        self.daily_trades[pair] += 1
        self.logger.info(f"Trade placed: {pair}, {direction}, Units: {units}, Confidence: {confidence}")

    async def run_trading_loop(self):
        """Continuously monitor market and place trades."""
        while True:
            open_trades = self.oanda.get_open_trades()
            if len(open_trades) >= self.max_open_trades:
                await asyncio.sleep(60)
                continue
            signals = await self.generate_signals()
            for pair, (direction, confidence) in signals.items():
                if any(t['pair'] == pair for t in open_trades) or self.daily_trades[pair] >= self.max_trades_per_day:
                    continue
                if confidence > 0.5:
                    for attempt in range(3):
                        try:
                            await self.place_trade(pair, direction, confidence)
                            break
                        except Exception as e:
                            self.logger.error(f"Trade attempt {attempt + 1} failed for {pair}: {e}")
                            if attempt == 2:
                                await self.telegram.send_message(f"Trade failed for {pair} after 3 attempts: {e}")
                            await asyncio.sleep(5)
            await asyncio.sleep(60)  # Check every minute

    async def monitor_trades(self):
        """Monitor open trades and close based on conditions."""
        while True:
            open_trades = self.oanda.get_open_trades()
            for trade in open_trades:
                trade_id = trade['trade_id']
                entry_time = self.db.get_entry_time(trade_id)
                current_time = datetime.now(pytz.utc)
                duration = (current_time - entry_time).total_seconds() / 3600
                if duration > 2 or trade['unrealized_pl'] > 0:
                    pl = self.oanda.close_trade(trade_id)
                    usd_gbp = await self.get_usd_gbp_rate()
                    self.db.update_trade(trade_id, status='closed', exit_price=trade['entry_price'] + trade['unrealized_pl'], pl=pl)
                    self.logger.info(f"Trade {trade_id} closed. P/L: ${pl}, £{pl * usd_gbp:.2f}")
            await asyncio.sleep(15)  # Check every 15 seconds

    async def execute_manual_trade(self):
        """Execute a trade triggered by /maketrade command."""
        signals = await self.generate_signals()
        best_pair, best_confidence, best_direction = None, 0, None
        open_trades = {t['pair'] for t in self.oanda.get_open_trades()}
        for pair, (direction, confidence) in signals.items():
            if pair in open_trades or self.daily_trades[pair] >= self.max_trades_per_day:
                continue
            if confidence > best_confidence and confidence > 0.75:
                best_pair, best_confidence, best_direction = pair, confidence, direction
        if best_pair:
