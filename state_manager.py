import asyncio
import aiofiles
import json
import os
import shutil
import time
import logging
from typing import Any, Dict
from datetime import datetime
from threading import Lock

STATE_FILE = "trade_state.json"
BACKUP_DIR = "state_backups"
MAX_BACKUPS = 12

file_lock = Lock()
save_lock = asyncio.Lock()

class StateManager:
    """StateManager class handles loading, saving, and maintaining integrity of application state using JSON files.
    Parameters:
        - None
    Processing Logic:
        - Ensures required directories exist and performs initial integrity check on startup.
        - Uses locks for safe concurrent file access during state reading and saving.
        - Automates backup management with timestamped filenames and periodic trimming of old backups.
        - Provides utility methods for state manipulation: get, set, delete, get_all."""
    def __init__(self):
        self.state: Dict[str, Any] = {}
        self.last_save_time = 0
        os.makedirs(BACKUP_DIR, exist_ok=True)
        self._integrity_check()

    def _integrity_check(self) -> None:
        """Performs an integrity check on a state file to ensure it exists and contains valid JSON data.
        Parameters:
            None
        Returns:
            None
        Processing Logic:
            - If the state file does not exist, an empty state is initialized.
            - Attempts to load the state file as JSON; if an error occurs, logs the error.
            - Upon detecting corruption, backs up the corrupted file with a timestamped name.
            - Resets state to empty when the file is determined to be corrupted."""
        if not os.path.exists(STATE_FILE):
            self._write_state_sync({})
            return
        try:
            with open(STATE_FILE, "r") as f:
                json.load(f)
        except Exception as e:
            logging.error(f"State file corrupted: {e}, backing up and resetting.")
            timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
            corrupted_name = f"corrupted_{timestamp}.json"
            shutil.copy(STATE_FILE, corrupted_name)
            self._write_state_sync({})

    def load_state(self) -> None:
        """Load the state from a predefined file and update the internal state attribute.
        Parameters:
            - None
        Returns:
            - None
        Processing Logic:
            - Acquires a file lock before attempting to read the state file.
            - Attempts to read and parse the state from a JSON file.
            - Logs an error and resets state to an empty dictionary if loading fails."""
        with file_lock:
            try:
                with open(STATE_FILE, "r") as f:
                    self.state = json.load(f)
            except Exception as e:
                logging.error(f"Failed to load state: {e}")
                self.state = {}

    def get(self, key: str, default: Any = None) -> Any:
        return self.state.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self.state[key] = value

    def delete(self, key: str) -> None:
        if key in self.state:
            del self.state[key]

    def get_all(self) -> Dict[str, Any]:
        return self.state

    def save(self) -> None:
        # Fire and forget async save
        asyncio.create_task(self._save_async())

    async def _save_async(self) -> None:
        """Saves the current state asynchronously to a file.
        Parameters:
            - None
        Returns:
            - None
        Processing Logic:
            - Acquires a save lock to ensure atomic writing of state to file.
            - Writes the state serialized in JSON format to a temporary file.
            - Replaces the actual state file with the temporary file upon successful write.
            - Logs an error if an exception occurs during the saving process."""
        async with save_lock:
            try:
                tmp_path = f"{STATE_FILE}.tmp"
                async with aiofiles.open(tmp_path, "w") as f:
                    await f.write(json.dumps(self.state, indent=2))
                os.replace(tmp_path, STATE_FILE)
                self._maybe_backup()
            except Exception as e:
                logging.error(f"Failed to save state: {e}")

    def _write_state_sync(self, state: Dict[str, Any]) -> None:
        try:
            with open(STATE_FILE, "w") as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            logging.error(f"Sync write failed: {e}")

    def _maybe_backup(self) -> None:
        """Periodically backs up a state file to a designated directory if the last backup occurred more than 5 minutes ago.
        Parameters:
            - None
        Returns:
            - None
        Processing Logic:
            - Checks if more than 300 seconds have passed since the last save to determine if a backup is needed.
            - Generates a timestamped filename for the backup.
            - Attempts to copy the state file to the backup directory and logs any exceptions that occur during the process.
            - Calls a function to trim old backups after successfully creating a new backup."""
        now = time.time()
        if now - self.last_save_time > 300:
            self.last_save_time = now
            timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
            backup_file = os.path.join(BACKUP_DIR, f"state_{timestamp}.json")
            try:
                shutil.copy(STATE_FILE, backup_file)
            except Exception as e:
                logging.error(f"Backup failed: {e}")
            self._trim_backups()

    def _trim_backups(self) -> None:
        """Trim old backups if the number of backup files exceeds the maximum allowed.
        Parameters:
            - None
        Returns:
            - None: This function does not return any value.
        Processing Logic:
            - Sorts the list of backup files in alphabetical order.
            - Removes the oldest backup files until the count is below or equal to MAX_BACKUPS.
            - Logs errors if file deletion fails or if the directory listing fails."""
        try:
            files = sorted(os.listdir(BACKUP_DIR))
            while len(files) > MAX_BACKUPS:
                old_file = files.pop(0)
                try:
                    os.remove(os.path.join(BACKUP_DIR, old_file))
                except Exception as e:
                    logging.error(f"Failed to delete old backup {old_file}: {e}")
        except Exception as e:
            logging.error(f"Failed to trim backups: {e}")

def reset_daily_counters(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Resets daily counters in the state dictionary for a fresh trading day.
    Adjust keys as per your actual state structure.
    """
    if 'daily_trades' in state:
        state['daily_trades'] = 0
    if 'daily_profit' in state:
        state['daily_profit'] = 0.0
    if 'daily_loss' in state:
        state['daily_loss'] = 0.0
    # Add more daily counters as needed
    return state

# Standalone async state helpers for use in other modules
_state_manager_instance = None

def _get_state_manager():
    global _state_manager_instance
    if _state_manager_instance is None:
        _state_manager_instance = StateManager()
        _state_manager_instance.load_state()
    return _state_manager_instance

async def record_open_trade(trade_id, instrument, direction, size, atr):
    """Records the details of an open trade and stores them in the state manager.
    Parameters:
        - trade_id (str): Unique identifier for the trade.
        - instrument (str): Financial instrument being traded.
        - direction (str): Direction of the trade, e.g., 'buy' or 'sell'.
        - size (float): Size of the trade.
        - atr (float): Average True Range used to measure the volatility.
    Returns:
        - None: This function does not return any value.
    Processing Logic:
        - Retrieves the current list of open trades from the state manager.
        - Appends the new trade details to the list.
        - Saves the updated list back to the state manager."""
    sm = _get_state_manager()
    open_trades = sm.get('open_trades', [])
    open_trades.append({
        'trade_id': trade_id,
        'instrument': instrument,
        'direction': direction,
        'size': size,
        'atr': atr,
        'opened_at': datetime.utcnow().isoformat()
    })
    sm.set('open_trades', open_trades)
    sm.save()

async def get_state():
    sm = _get_state_manager()
    return sm.get_all()

async def get_account_summary():
    from oanda_client import get_account_summary as oanda_get_account_summary
    return await oanda_get_account_summary()

async def load_state():
    sm = _get_state_manager()
    sm.load_state()
    return sm.get_all()
 