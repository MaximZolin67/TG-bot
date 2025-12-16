import sqlite3 
DB_PATH = "shop.db"
conn = sqlite3.connect(DB_PATH)
c = conn.cursor()
# c.execute("update users set role = 'admin' where id = 1") 
c.execute("delete from keys ") 
conn.commit()
conn.close()

