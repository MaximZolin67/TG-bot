import sqlite3 
DB_PATH = "shop.db"
conn = sqlite3.connect(DB_PATH)
c = conn.cursor()
c.execute("UPDATE payments SET full_receipt = 'https://yadi.sk/d/742sfq2ojwnksQ' where id = 5 ") 
conn.commit()
conn.close()

