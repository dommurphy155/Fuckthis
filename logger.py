import logging
import os
import asyncio
from config import setup_logger

trade_logger = setup_logger("trade_actions")
info_logger = setup_logger("info")

async def log_trade_action(*args, **kwargs):
    msg = " ".join(str(a) for a in args)
    trade_logger.info(msg)

async def log_info(*args, **kwargs):
    msg = " ".join(str(a) for a in args)
    info_logger.info(msg)