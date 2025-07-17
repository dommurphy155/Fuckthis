import logging
import os
from datetime import datetime
import pytz

def setup_logger():
    """Set up logging to a file with UK timestamps."""
    if not os.path.exists('logs'):
        os.makedirs('logs')
    logger = logging.getLogger('ForexBot')
    logger.setLevel(logging.INFO)
    handler = logging.FileHandler('logs/trade.log')
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    # Override time to use UK timezone
    def time_func():
        return datetime.now(pytz.timezone('Europe/London')).timestamp()
    logging.Formatter.converter = lambda *args: datetime.fromtimestamp(time_func(), pytz.timezone('Europe/London'))
    
    return logger
 