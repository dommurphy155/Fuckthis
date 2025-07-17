import os
import sys
import logging
from datetime import datetime

LOGS_DIR = "logs"
os.makedirs(LOGS_DIR, exist_ok=True)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
MAX_COMMANDS_PER_MIN = int(os.environ.get("MAX_COMMANDS_PER_MIN", 10))


def setup_logger(name: str):
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )

    file_handler = logging.FileHandler(os.path.join(LOGS_DIR, f"{name}.log"))
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


def rotate_logs():
    now = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
    for filename in os.listdir(LOGS_DIR):
        if filename.endswith(".log"):
            old_path = os.path.join(LOGS_DIR, filename)
            new_path = os.path.join(LOGS_DIR, f"{filename}.{now}")
            os.rename(old_path, new_path)
