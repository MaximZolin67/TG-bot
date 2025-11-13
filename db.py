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
        role TEXT DEFAULT 'user',
        referral_bonus_given INTEGER DEFAULT 0
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

    c.execute('''CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        amount REAL,
        payment_id TEXT,
        status TEXT DEFAULT 'на рассмотрении',
        order_name TEXT,
        details TEXT,
        full_receipt TEXT
    )''')

    conn.commit()
    conn.close()

def is_admin(telegram_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT role FROM users WHERE telegram_id = ?", (telegram_id,))
    row = c.fetchone()
    conn.close()
    return row and row[0] == "admin"

def get_pending_payments():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT id, user_id, amount, order_name, status, full_receipt
        FROM payments
        WHERE status = 'На рассмотрении'
        ORDER BY id DESC
    """)
    rows = c.fetchall()
    conn.close()
    return rows

def get_all_payments():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT id, user_id, amount, order_name, status, full_receipt
        FROM payments
        ORDER BY id DESC
    """)
    rows = c.fetchall()
    conn.close()
    return rows

def add_user(telegram_id, referrer=None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id FROM users WHERE telegram_id = ?", (telegram_id,))
    if c.fetchone() is None:
        c.execute(
            "INSERT INTO users (telegram_id, referrer) VALUES (?, ?)", (telegram_id, referrer)
        )
    conn.commit()
    conn.close()

def get_balance(telegram_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT balance FROM users WHERE telegram_id = ?", (telegram_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return float(row[0])
    return 0.0

def update_balance(telegram_id, amount):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE users SET balance = balance + ? WHERE telegram_id = ?", (amount, telegram_id))
    conn.commit()
    conn.close()

def create_payment(user_id, amount, order_name, details):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''INSERT INTO payments (user_id, amount, order_name, details) VALUES (?, ?, ?, ?)''',
              (user_id, amount, order_name, details))
    conn.commit()
    payment_id = c.lastrowid
    conn.close()
    return payment_id

def save_receipt(payment_id, file_url):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE payments SET full_receipt = ? WHERE id = ?", (file_url, payment_id))
    conn.commit()
    conn.close()

def get_payment(payment_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM payments WHERE id = ?", (payment_id,))
    payment = c.fetchone()
    conn.close()
    return payment

def set_payment_status(payment_id, status):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE payments SET status = ? WHERE id = ?", (status, payment_id))
    conn.commit()
    conn.close()

def get_all_products():
    conn = sqlite3.connect(DB_PATH)
    products = conn.execute("SELECT id, name, description, price FROM products").fetchall()
    conn.close()
    return products

def get_product_by_id(product_id):
    conn = sqlite3.connect(DB_PATH)
    product = conn.execute("SELECT id, name, description, price FROM products WHERE id = ?", (product_id,)).fetchone()
    conn.close()
    return product

def buy_key_by_product_id(product_id, user_telegram_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, key FROM keys WHERE product_id = ? AND user_id IS NULL LIMIT 1", (product_id,))
    row = c.fetchone()
    if row:
        key_id, key_value = row
        c.execute("SELECT balance FROM users WHERE telegram_id = ?", (user_telegram_id,))
        user_balance_row = c.fetchone()
        c.execute("SELECT price FROM products WHERE id = ?", (product_id,))
        price = c.fetchone()[0]
        if not user_balance_row or user_balance_row[0] < price:
            conn.close()
            return None
        c.execute("UPDATE users SET balance = balance - ? WHERE telegram_id = ?", (price, user_telegram_id))
        c.execute("UPDATE keys SET user_id = ? WHERE id = ?", (user_telegram_id, key_id))
        conn.commit()
        conn.close()
        return key_value
    conn.close()
    return None

def check_and_grant_referral_bonus(user_telegram_id):
    BONUS_SUM = 100
    REFERRAL_THRESHOLD = 2000

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("SELECT id, referrer, referral_bonus_given FROM users WHERE telegram_id = ?", (user_telegram_id,))
    user_data = c.fetchone()
    if not user_data:
        conn.close()
        return
    user_id, referrer_id, bonus_given = user_data

    if referrer_id is None or bonus_given:
        conn.close()
        return

    c.execute("""
        SELECT SUM(p.price) FROM keys k
        JOIN products p ON k.product_id = p.id
        WHERE k.user_id = ?
    """, (user_id,))
    total_sum = c.fetchone()[0] or 0

    if total_sum >= REFERRAL_THRESHOLD:
        c.execute("SELECT telegram_id FROM users WHERE id = ?", (referrer_id,))
        referrer_telegram = c.fetchone()
        if referrer_telegram:
            c.execute(
                "UPDATE users SET balance = balance + ?, referral_bonus_given = 1 WHERE id = ?",
                (BONUS_SUM, referrer_id)
            )
            conn.commit()
    conn.close()
