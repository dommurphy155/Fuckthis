import asyncio
import os
import logging
from typing import Any, Dict, List, Optional
from functools import wraps
import oandapyV20
import oandapyV20.endpoints.accounts as accounts
import oandapyV20.endpoints.orders as orders
import oandapyV20.endpoints.positions as positions
import oandapyV20.endpoints.trades as trades

def retry_async(retries=5, delay=2):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            for attempt in range(retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    logging.error(f"Retry {attempt+1}/{retries} for {func.__name__}: {e}")
                    await asyncio.sleep(delay)
            raise Exception(f"Failed after {retries} retries: {func.__name__}")
        return wrapper
    return decorator

class OandaClient:
    def __init__(self, access_token: str = None, account_id: str = None, environment: str = None):
        self.access_token = access_token or os.environ.get("OANDA_API_KEY")
        self.account_id = account_id or os.environ.get("OANDA_ACCOUNT_ID")
        self.environment = environment or os.environ.get("OANDA_ENV", "practice")
        self.client = oandapyV20.API(access_token=self.access_token, environment=self.environment)

    def get_account_summary(self) -> Optional[Dict[str, Any]]:
        try:
            r = accounts.AccountSummary(accountID=self.account_id)
            self.client.request(r)
            return r.response.get('account', None)
        except Exception as e:
            logging.error(f"Error getting account summary: {e}")
            return None

    def get_open_positions(self) -> List[Dict[str, Any]]:
        try:
            r = positions.OpenPositions(accountID=self.account_id)
            self.client.request(r)
            return r.response.get('positions', [])
        except Exception as e:
            logging.error(f"Error getting open positions: {e}")
            return []

    def get_open_trades(self) -> List[Dict[str, Any]]:
        try:
            r = trades.OpenTrades(accountID=self.account_id)
            self.client.request(r)
            return r.response.get('trades', [])
        except Exception as e:
            logging.error(f"Error getting open trades: {e}")
            return []

    def place_order(
        self,
        instrument: str,
        units: int,
        order_type: str = "MARKET",
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None
    ) -> Optional[Dict[str, Any]]:
        try:
            order_data = {
                "order": {
                    "instrument": instrument,
                    "units": str(units),
                    "type": order_type,
                    "positionFill": "DEFAULT"
                }
            }
            if stop_loss is not None:
                order_data["order"]["stopLossOnFill"] = {"price": str(stop_loss)}
            if take_profit is not None:
                order_data["order"]["takeProfitOnFill"] = {"price": str(take_profit)}
            r = orders.OrderCreate(accountID=self.account_id, data=order_data)
            self.client.request(r)
            return r.response
        except Exception as e:
            logging.error(f"Error placing order: {e}")
            return None

    def close_trade(self, trade_id: str) -> Optional[Dict[str, Any]]:
        try:
            r = trades.TradeClose(accountID=self.account_id, tradeID=trade_id)
            self.client.request(r)
            return r.response
        except Exception as e:
            logging.error(f"Error closing trade {trade_id}: {e}")
            return None

# Standalone async wrappers for use in other modules
@retry_async()
async def get_open_positions():
    loop = asyncio.get_event_loop()
    client = OandaClient()
    return await loop.run_in_executor(None, client.get_open_positions)

@retry_async()
async def get_account_summary():
    loop = asyncio.get_event_loop()
    client = OandaClient()
    return await loop.run_in_executor(None, client.get_account_summary)

@retry_async()
async def close_trade_by_id(trade_id: str):
    loop = asyncio.get_event_loop()
    client = OandaClient()
    return await loop.run_in_executor(None, client.close_trade, trade_id)
 