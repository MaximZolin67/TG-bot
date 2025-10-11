import sqlite3
from config import DB_PATH

def fill_test_data():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Добавляем тестовые продукты
    products = [
        ("Антивирус PRO", "Лицензионный антивирус для защиты ПК", 500),
        ("Офисный пакет", "Полный офисный пакет для работы с документами", 1500),
        ("Игра CyberX", "Новая футуристическая игра с киберпанк сюжетом", 1200),
    ]
    c.executemany(
        "INSERT OR IGNORE INTO products (name, description, price) VALUES (?, ?, ?)",
        products
    )
    conn.commit()

    # Получаем id добавленных продуктов
    c.execute("SELECT id, name FROM products")
    products_db = c.fetchall()
    product_ids = {name: pid for pid, name in products_db}

    # Добавляем ключи к каждому продукту
    keys = [
        # Для Антивирус PRO
        (product_ids["Антивирус PRO"], "ANTIVIRUS-1234-ABCD-5678"),
        (product_ids["Антивирус PRO"], "ANTIVIRUS-2345-BCDE-6789"),
        # Для Офисного пакета
        (product_ids["Офисный пакет"], "OFFICE-9876-YTRE-5432"),
        (product_ids["Офисный пакет"], "OFFICE-8765-UIOP-4321"),
        # Для Игры CyberX
        (product_ids["Игра CyberX"], "CYBERX-5555-AAAA-9999"),
    ]
    c.executemany(
        "INSERT OR IGNORE INTO keys (product_id, key, user_id) VALUES (?, ?, NULL)", keys
    )
    conn.commit()
    conn.close()
    print("Тестовые данные успешно добавлены.")

if __name__ == "__main__":
    fill_test_data()
