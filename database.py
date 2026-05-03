import logging
import os
import sqlite3
from contextlib import closing
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

DB_FILE = os.path.join(os.path.dirname(os.path.realpath(__file__)), "habit.db")

META_KEY_OFFSET = 'offset'
DATE_FORMAT = "%Y-%m-%d"


def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with closing(get_db_connection()) as conn:
        # WAL mode allows safe concurrent access from API + button_listener
        conn.execute("PRAGMA journal_mode=WAL")

        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS meta (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON logs(timestamp)
        ''')

        conn.commit()


def add_log(timestamp: Optional[str] = None) -> None:
    if timestamp is None:
        timestamp = datetime.now().isoformat()
    else:
        datetime.fromisoformat(timestamp)  # raises ValueError on bad input

    with closing(get_db_connection()) as conn:
        conn.execute('INSERT INTO logs (timestamp) VALUES (?)', (timestamp,))
        conn.commit()


def get_all_logs() -> list[str]:
    with closing(get_db_connection()) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT timestamp FROM logs ORDER BY timestamp ASC')
        return [row['timestamp'] for row in cursor.fetchall()]


def get_logs_since(since_date: str) -> list[str]:
    """Fetch logs with timestamp >= since_date (ISO format string)."""
    with closing(get_db_connection()) as conn:
        cursor = conn.cursor()
        cursor.execute(
            'SELECT timestamp FROM logs WHERE timestamp >= ? ORDER BY timestamp ASC',
            (since_date,)
        )
        return [row['timestamp'] for row in cursor.fetchall()]


def get_offset() -> int:
    with closing(get_db_connection()) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT value FROM meta WHERE key = ?', (META_KEY_OFFSET,))
        row = cursor.fetchone()
        if row:
            return int(row['value'])
        return 0


def get_log_count() -> int:
    """Return total number of logs without fetching all rows."""
    with closing(get_db_connection()) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM logs')
        return cursor.fetchone()[0]


def get_logs_for_date(date_str: str) -> list[dict]:
    """Return logs for a specific date as list of {"id": int, "timestamp": str}."""
    next_day = (datetime.strptime(date_str, DATE_FORMAT) + timedelta(days=1)).strftime(DATE_FORMAT)
    with closing(get_db_connection()) as conn:
        cursor = conn.cursor()
        cursor.execute(
            'SELECT id, timestamp FROM logs WHERE timestamp >= ? AND timestamp < ? ORDER BY timestamp ASC',
            (date_str, next_day)
        )
        return [{"id": row["id"], "timestamp": row["timestamp"]} for row in cursor.fetchall()]


def delete_log(log_id: int) -> bool:
    """Delete a log by id. Returns True if deleted, False if not found."""
    with closing(get_db_connection()) as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM logs WHERE id = ?', (log_id,))
        conn.commit()
        return cursor.rowcount > 0


def set_offset(offset: int) -> None:
    with closing(get_db_connection()) as conn:
        conn.execute(
            'INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)',
            (META_KEY_OFFSET, str(offset))
        )
        conn.commit()
