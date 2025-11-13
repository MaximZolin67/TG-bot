# import sqlite3 
# DB_PATH = "shop.db"
# conn = sqlite3.connect(DB_PATH)
# c = conn.cursor()
# c.execute("UPDATE users SET balance = ' 0 ' ") 
# conn.commit()
# conn.close()

# from pydrive2.auth import GoogleAuth
# from pydrive2.drive import GoogleDrive

# gauth = GoogleAuth()
# gauth.LoadCredentialsFile("token.json")

# if gauth.access_token_expired:
#     gauth.Refresh()
# gauth.SaveCredentialsFile("token.json")

# # gauth = GoogleAuth()
# # gauth.LocalWebserverAuth()  # 1 раз откроет браузер
# # gauth.SaveCredentialsFile("token.json")

# drive = GoogleDrive(gauth)
# file1 = drive.CreateFile({'title': 'main.py'})
# file1.SetContentString('hello')
# file1.Upload() # Files.insert()
# file1.InsertPermission({"role": "reader","type": "anyone"})
# print(file1['alternateLink'])
from db import (get_all_payments,)
print (get_all_payments())
