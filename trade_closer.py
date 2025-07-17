import asyncio
from oanda_client import close_trade_by_id, get_open_positions
from logger import log_trade_action

async def close_all_trades(manual_override=False):
    open_positions = await get_open_positions()
    if not open_positions:
        return "No open positions to close."

    results = []
    for position in open_positions:
        for side in ["long", "short"]:
            units = int(position[side]["units"])
            if units != 0:
                trade_id = position[side]["tradeIDs"][0]
                result = await close_trade_by_id(trade_id)
                results.append(f"Closed {side.upper()} {position['instrument']} - {units} units: {result}")
                await log_trade_action(f"Closed trade {trade_id} on {position['instrument']} ({side}) - {result}")

                # Sleep to respect rate limits
                await asyncio.sleep(0.5)

    return "\n".join(results)
