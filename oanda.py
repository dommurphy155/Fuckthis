# oanda.py
import os
import oandapyV20
import oandapyV20.endpoints.accounts as accounts
import oandapyV20.endpoints.orders as orders
import oandapyV20.endpoints.trades as trades
import oandapyV20.endpoints.pricing as pricing


class OANDAClient:
    def __init__(self):
        self.client = oandapyV20.API(access_token=os.environ["OANDA_API_KEY"])
        self.account_id = os.environ["OANDA_ACCOUNT_ID"]

    def get_account_summary(self):
        r = accounts.AccountSummary(self.account_id)
        self.client.request(r)
        return r.response

    def place_market_order(self, instrument, units, stop_loss_price=None):
        order_data = {
            "order": {
                "instrument": instrument,
                "units": str(units),
                "type": "MARKET",
                "positionFill": "DEFAULT"
            }
        }
        if stop_loss_price:
            order_data["order"]["stopLossOnFill"] = {
                "price": str(stop_loss_price)
            }

        r = orders.OrderCreate(accountID=self.account_id, data=order_data)
        self.client.request(r)
        return r.response

    def close_trade(self, trade_id):
        r = trades.TradeClose(accountID=self.account_id, tradeID=trade_id)
        self.client.request(r)
        return r.response

    def get_latest_price(self, instrument):
        r = pricing.PricingInfo(accountID=self.account_id, params={"instruments": instrument})
        self.client.request(r)
        return r.response["prices"][0]
