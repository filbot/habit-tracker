import sqlite3
import os
from datetime import datetime

DB_FILE = os.path.join(os.path.dirname(os.path.realpath(__file__)), "habit.db")

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
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
    
    conn.commit()
    conn.close()

def add_log(timestamp=None):
    if timestamp is None:
        timestamp = datetime.now().isoformat()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO logs (timestamp) VALUES (?)', (timestamp,))
    conn.commit()
    conn.close()

def get_all_logs():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT timestamp FROM logs ORDER BY timestamp ASC')
    rows = cursor.fetchall()
    conn.close()
    return [row['timestamp'] for row in rows]

def get_offset():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT value FROM meta WHERE key = ?', ('offset',))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return int(row['value'])
    return 0

def set_offset(offset):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)', ('offset', str(offset)))
    conn.commit()
    conn.close()
