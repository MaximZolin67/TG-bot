import sqlite3
from config import DB_PATH

def fill_products():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    with open("data/products.csv", "r", encoding="utf-8") as file:
        file.readline()  # Пропускаем заголовок
        products = []
        for line in file:
            p = line.strip().split("|")
            products.append((p[0], p[1], int(p[2])))

    c.executemany(
        "INSERT OR IGNORE INTO products (name, description, price) VALUES (?, ?, ?)",
        products
    )
    conn.commit()
    conn.close()

if __name__ == "__main__":
    fill_products()