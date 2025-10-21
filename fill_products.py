import sqlite3
from config import DB_PATH

def fill_products():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    file = open("data/products.csv")
    file.readline()
    products = []
    for line in file:
        p = line.split("|")
        products.append((p[0], p[1], int(p[2])))

    c.executemany(
        "INSERT OR IGNORE INTO products (name, description, price) VALUES (?, ?, ?)",
        products
    )
    conn.commit()

if __name__ == "__main__":
    fill_products()
