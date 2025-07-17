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
    """Decorator to retry an asynchronous function upon exception.
    Parameters:
        - retries (int): The number of retry attempts before raising an exception. Default is 5.
        - delay (int or float): The delay between retries, in seconds. Default is 2.
    Returns:
        - function: A wrapper function that retries the execution of the decorated async function.
    Processing Logic:
        - Logs an error message for each retry attempt.
        - Awaits the specified delay between each retry attempt.
        - Raises an exception if the function fails after all retry attempts."""
    def decorator(func):
        @wraps(func)
        """Decorator for retrying an asynchronous function upon encountering an exception.
        Parameters:
            - func (Callable): The asynchronous function to be executed with retries.
        Returns:
            - Callable: A wrapped asynchronous function that includes retry logic.
        Processing Logic:
            - Logs an error message with the retry attempt count and exception details.
            - Waits for a specified delay before attempting the next retry.
            - Raises an exception after all retries fail."""
        async def wrapper(*args, **kwargs):
            """Attempt to execute an asynchronous function multiple times with retries on failure.
            Parameters:
                - retries (int): The number of retry attempts allowed before giving up.
                - delay (float): The delay in seconds between retry attempts.
            Returns:
                - Type-varies: The result of the successfully executed asynchronous function.
            Processing Logic:
                - Attempts to execute the function `retries` number of times in case of exceptions.
                - Logs the error message with the attempt number.
                - Waits for `delay` seconds between retry attempts using asyncio sleep.
                - Raises an exception if all retry attempts fail."""
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
        """Retrieves the summary of an account.
        Parameters:
            - None
        Returns:
            - Optional[Dict[str, Any]]: A dictionary containing the account summary details if successful, None otherwise.
        Processing Logic:
            - Constructs an AccountSummary request using the accountID.
            - Attempts to execute the request using the client.
            - Logs an error message if the request fails and returns None."""
        try:
            r = accounts.AccountSummary(accountID=self.account_id)
            self.client.request(r)
            return r.response.get('account', None)
        except Exception as e:
            logging.error(f"Error getting account summary: {e}")
            return None

    def get_open_positions(self) -> List[Dict[str, Any]]:
        """Retrieve a list of open trading positions from the account.
        Parameters:
            - None
        Returns:
            - List[Dict[str, Any]]: A list of dictionaries representing the open trading positions. If an error occurs, returns an empty list.
        Processing Logic:
            - Sends a request to retrieve open positions using the specified account ID.
            - Logs any exceptions that occur during the request."""
        try:
            r = positions.OpenPositions(accountID=self.account_id)
            self.client.request(r)
            return r.response.get('positions', [])
        except Exception as e:
            logging.error(f"Error getting open positions: {e}")
            return []

    def get_open_trades(self) -> List[Dict[str, Any]]:
        """Retrieve open trades for the given account.
        Parameters:
            - self: An instance of the class where this method is defined.
        Returns:
            - List[Dict[str, Any]]: A list of dictionaries representing open trades.
        Processing Logic:
            - Initiates a request to fetch open trades using accountID.
            - Logs errors if the request fails and returns an empty list in such cases."""
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
        """Place an order for a specified financial instrument with optional risk management parameters.
        Parameters:
            - instrument (str): The name or symbol of the financial instrument to be traded.
            - units (int): The number of units to be ordered; can be positive for buy or negative for sell.
            - order_type (str, optional): The type of order to place (default is "MARKET").
            - stop_loss (Optional[float], optional): Price level to automatically sell the instrument if it drops to this value.
            - take_profit (Optional[float], optional): Price level to automatically sell the instrument if it rises to this value.
        Returns:
            - Optional[Dict[str, Any]]: Details of the placed order if successful, None otherwise.
        Processing Logic:
            - Creates an order data dictionary that includes order specifics such as instrument, units, and type.
            - Adds stop loss and take profit stipulations to the order data if provided.
            - Attempts to place the order using the client request method and logs an error in case of failure."""
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
        """Closes an existing trade for a given trade ID.
        Parameters:
            - trade_id (str): The unique identifier of the trade to be closed.
        Returns:
            - Optional[Dict[str, Any]]: Returns the response containing details of the closed trade if successful; otherwise, returns None.
        Processing Logic:
            - Initiates a request to close the trade using the specified trade ID.
            - Logs an error message if the trade closure request fails due to an exception."""
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
 