import os
import sys
import logging
from datetime import datetime

LOGS_DIR = "logs"
os.makedirs(LOGS_DIR, exist_ok=True)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
MAX_COMMANDS_PER_MIN = int(os.environ.get("MAX_COMMANDS_PER_MIN", 10))

OANDA_API_KEY = os.environ.get("OANDA_API_KEY")
OANDA_ACCOUNT_ID = os.environ.get("OANDA_ACCOUNT_ID")
OANDA_API_URL = os.environ.get("OANDA_API_URL")
OANDA_ENV = os.environ.get("OANDA_ENV", "practice")

LOG_FILE_PERMISSION = 0o600


def setup_logger(name: str):
    """Sets up a logger with both file and console handlers for debugging and informational messages.
    Parameters:
        - name (str): The name assigned to the logger, used for log file naming.
    Returns:
        - logging.Logger: Configured logger instance capable of writing logs to a file and outputting to console.
    Processing Logic:
        - Uses `logging.DEBUG` level for file logs and `logging.INFO` level for console logs.
        - File logs are saved in a predetermined directory with standardized formatting and permissions.
        - Configures log message format to include timestamps, log level, and message content."""
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )

    file_path = os.path.join(LOGS_DIR, f"{name}.log")
    file_handler = logging.FileHandler(file_path)
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)
    try:
        os.chmod(file_path, LOG_FILE_PERMISSION)
    except Exception:
        pass

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)
    logger.addHandler(console_handler)

    return logger


def rotate_logs():
    now = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
    for filename in os.listdir(LOGS_DIR):
        if filename.endswith(".log"):
            old_path = os.path.join(LOGS_DIR, filename)
            new_path = os.path.join(LOGS_DIR, f"{filename}.{now}")
            os.rename(old_path, new_path)
