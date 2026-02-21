import requests
import csv
import time
from datetime import datetime

TOKEN = "8526408120:AAHqYHx3n9V3qpAqbp8_UDwfWed5SHC7Wbo"
CHAT_ID = "8559067633"

CSV_FILE = "Jadwal_Route_Siborong_Borong.csv"

print("🔔 BOT LOGISTIK AKTIF 24 JAM")

def kirim(pesan):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": pesan}
    requests.post(url, data=data)

while True:
    now = datetime.now().strftime("%H:%M")

    with open(CSV_FILE, newline='', encoding='utf-8') as file:
        data = csv.DictReader(file)

        for row in data:

            start_loading = row["Start Loading"]
            selesai_loading = row["Selesai Loading"]

            if now == start_loading:
                kirim(f"🚚 START LOADING SEKARANG\nJam: {start_loading}")

            if now == selesai_loading:
                kirim(f"✅ SELESAI LOADING\nJam: {selesai_loading}")

    time.sleep(60)
