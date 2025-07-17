import asyncio
from oanda_client import close_trade_by_id, get_open_positions
from logger import log_trade_action

async def close_all_trades(manual_override=False):
    """Close all open trades asynchronously, considering manual override option.
    Parameters:
        - manual_override (bool): Indicates whether the closure is being done manually. Default is False.
    Returns:
        - str: A summary report of the trades closed, or a message stating no open positions.
    Processing Logic:
        - Fetch all open positions using an asynchronous call.
        - Loop through each position and attempt to close both long and short positions if any units are present.
        - Close trades by using the trade ID associated with each position.
        - Log each trade closure action for record-keeping and processing consistency."""
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
