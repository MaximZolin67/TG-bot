import sqlite3
from config import DB_PATH


def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id INTEGER UNIQUE,
        balance REAL DEFAULT 0,
        referrer INTEGER,
        role TEXT DEFAULT 'user'
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        description TEXT,
        price INTEGER NOT NULL
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS keys (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER NOT NULL,
        key TEXT UNIQUE NOT NULL,
        user_id INTEGER
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


def get_all_products():
    conn = sqlite3.connect(DB_PATH)
    products = conn.execute("SELECT id, name, description, price FROM products").fetchall()
    conn.close()
    return products


def get_product_by_id(product_id):
    conn = sqlite3.connect(DB_PATH)
    product = conn.execute(
        "SELECT id, name, description, price FROM products WHERE id = ?", (product_id,)
    ).fetchone()
    conn.close()
    return product


def buy_key_by_product_id(product_id, user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "SELECT id, key FROM keys WHERE product_id = ? AND user_id IS NULL LIMIT 1",
        (product_id,)
    )
    row = c.fetchone()
    if row:
        key_id, key_value = row
        c.execute("UPDATE keys SET user_id = ? WHERE id = ?", (user_id, key_id))
        conn.commit()
        conn.close()
        return key_value
    conn.close()
    return None
