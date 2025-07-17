import sqlite3
from datetime import datetime
import pytz

class Database:
    """Manages SQLite database for trade data."""
    def __init__(self, db_file='trades.db'):
        self.conn = sqlite3.connect(db_file, check_same_thread=False)
        self.create_tables()

    def create_tables(self):
        """Create the trades table if it doesn't exist."""
        with self.conn:
            self.conn.execute('''
                CREATE TABLE IF NOT EXISTS trades (
                    trade_id TEXT PRIMARY KEY,
                    pair TEXT,
                    entry_timestamp TEXT,
                    confidence REAL,
                    expected_profit REAL,
                    sl REAL,
                    tp REAL,
                    position_size INTEGER,
                    entry_price REAL,
                    exit_timestamp TEXT,
                    exit_price REAL,
                    pl REAL,
                    status TEXT
                )
            ''')

    def insert_trade(self, trade_id, pair, entry_time, confidence, expected_profit, sl, tp, units, entry_price):
        """Insert a new trade into the database."""
        with self.conn:
            self.conn.execute('''
                INSERT INTO trades (trade_id, pair, entry_timestamp, confidence, expected_profit, sl, tp, position_size, entry_price, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (trade_id, pair, entry_time.isoformat(), confidence, expected_profit, sl, tp, units, entry_price, 'open'))

    def update_trade(self, trade_id, status, exit_price=None, pl=None):
        """Update trade status and exit details."""
        exit_time = datetime.now(pytz.utc).isoformat() if status == 'closed' else None
        with self.conn:
            if status == 'closed':
                self.conn.execute('''
                    UPDATE trades SET status=?, exit_timestamp=?, exit_price=?, pl=?
                    WHERE trade_id=?
                ''', (status, exit_time, exit_price, pl, trade_id))
            else:
                self.conn.execute('''
                    UPDATE trades SET status=?
                    WHERE trade_id=?
                ''', (status, trade_id))

    def get_entry_time(self, trade_id):
        """Get the entry timestamp of a trade."""
        with self.conn:
            cursor = self.conn.execute('SELECT entry_timestamp FROM trades WHERE trade_id=?', (trade_id,))
            result = cursor.fetchone()
            return datetime.fromisoformat(result[0]) if result else None

    def get_expected_profit(self, trade_id):
        """Get the expected profit of a trade."""
        with self.conn:
            cursor = self.conn.execute('SELECT expected_profit FROM trades WHERE trade_id=?', (trade_id,))
            result = cursor.fetchone()
            return result[0] if result else 0

    def get_trades_by_date(self, date):
        """Get all trades for a specific date."""
        start = datetime.combine(date, datetime.min.time(), tzinfo=pytz.utc).isoformat()
        end = datetime.combine(date, datetime.max.time(), tzinfo=pytz.utc).isoformat()
        with self.conn:
            cursor = self.conn.execute('''
                SELECT * FROM trades WHERE entry_timestamp BETWEEN ? AND ?
            ''', (start, end))
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def get_trades_by_period(self, start, end):
        """Get all trades within a date range."""
        with self.conn:
            cursor = self.conn.execute('''
                SELECT * FROM trades WHERE entry_timestamp BETWEEN ? AND ?
            ''', (start.isoformat(), end.isoformat()))
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
 