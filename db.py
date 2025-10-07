import sqlite3
from config import DB_PATH

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id INTEGER UNIQUE,
        balance REAL DEFAULT 0,
        referrer INTEGER
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS keys (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        key TEXT UNIQUE,
        sold INTEGER DEFAULT 0
    )''')

    conn.commit()
    conn.close()

def add_user(telegram_id, referrer=None):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT OR IGNORE INTO users (telegram_id, referrer) VALUES (?, ?)",
        (telegram_id, referrer)
    )
    conn.commit()
    conn.close()

def get_available_keys():
    conn = sqlite3.connect(DB_PATH)
    keys = conn.execute("SELECT id, key FROM keys WHERE sold = 0").fetchall()
    conn.close()
    return keys

def buy_key(key_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT key FROM keys WHERE id = ? AND sold = 0", (key_id,))
    row = c.fetchone()
    if row:
        c.execute("UPDATE keys SET sold = 1 WHERE id = ?", (key_id,))
        conn.commit()
        conn.close()
        return row[0]
    conn.close()
    return None
