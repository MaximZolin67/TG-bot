from db import delete_paid_payments
from config import(YANDEX_TOKEN)
import time
import yadisk
f = open("token.txt")
client = yadisk.Client(token=YANDEX_TOKEN)
while True:
    try:
        delete_paid_payments(client)
        time.sleep(3600)
    except Exception as e:
        print(e)