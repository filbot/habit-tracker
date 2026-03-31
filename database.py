import sqlite3
import os
import logging
from contextlib import closing
from datetime import datetime

logger = logging.getLogger(__name__)

DB_FILE = os.path.join(os.path.dirname(os.path.realpath(__file__)), "habit.db")

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with closing(get_db_connection()) as conn:
        cursor = conn.cursor()

        # Create logs table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL
            )
        ''')

        # Create meta table for offset and other config
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS meta (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')

        # Index for timestamp-based queries
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON logs(timestamp)
        ''')

        conn.commit()

def add_log(timestamp=None):
    if timestamp is None:
        timestamp = datetime.now().isoformat()
    else:
        # Validate timestamp format
        datetime.fromisoformat(timestamp)

    with closing(get_db_connection()) as conn:
        conn.execute('INSERT INTO logs (timestamp) VALUES (?)', (timestamp,))
        conn.commit()

def get_all_logs():
    with closing(get_db_connection()) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT timestamp FROM logs ORDER BY timestamp ASC')
        rows = cursor.fetchall()
        return [row['timestamp'] for row in rows]

def get_logs_since(since_date):
    """Fetch logs with timestamp >= since_date (ISO format string)."""
    with closing(get_db_connection()) as conn:
        cursor = conn.cursor()
        cursor.execute(
            'SELECT timestamp FROM logs WHERE timestamp >= ? ORDER BY timestamp ASC',
            (since_date,)
        )
        rows = cursor.fetchall()
        return [row['timestamp'] for row in rows]

def get_offset():
    with closing(get_db_connection()) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT value FROM meta WHERE key = ?', ('offset',))
        row = cursor.fetchone()

        if row:
            return int(row['value'])
        return 0

def get_log_count():
    """Return total number of logs without fetching all rows."""
    with closing(get_db_connection()) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM logs')
        return cursor.fetchone()[0]

def set_offset(offset):
    with closing(get_db_connection()) as conn:
        conn.execute('INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)', ('offset', str(offset)))
        conn.commit()
