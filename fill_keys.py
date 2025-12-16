import sqlite3
from config import DB_PATH

def fill_keys():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    with open("data/keys.csv", "r", encoding="utf-8") as file:
        file.readline()
        keys = []
        for line in file:
            p = line.strip().split("|")
            keys.append((int(p[0]), p[1],))

    c.executemany(
        "INSERT OR IGNORE INTO keys (product_id, key, user_id) VALUES (?, ?, NULL)",
        keys
    )
    conn.commit()
    conn.close()
    
if __name__ == "__main__":
    fill_keys()
