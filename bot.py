import requests
import csv
import time
from datetime import datetime, timedelta

TOKEN = "8526408120:AAHqYHx3n9V3qpAqbp8_UDwfWed5SHC7Wbo"
CHAT_ID = "8559067633"

CSV_FILE = "Jadwal_Route_Siborong_Borong.csv"

def kirim(pesan):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": pesan})

print("🔔 BOT LOGISTIK AKTIF 24 JAM")

sudah_kirim = set()

while True:
    sekarang = datetime.now().strftime("%H:%M")

    with open(CSV_FILE, newline='', encoding='utf-8') as f:
        data = csv.DictReader(f)

        for row in data:

            route = row["Route"]

            start = row["Start Loading"]
            selesai = row["Selesai Loading"]

            # 🔥 Reminder H-10 menit START
            waktu_start_minus = (
                datetime.strptime(start, "%H:%M") - timedelta(minutes=10)
            ).strftime("%H:%M")

            if sekarang == waktu_start_minus and ("rem_start", route) not in sudah_kirim:
                kirim(f"⏰ H-10 START LOADING\n{route}\nJam {start}")
                sudah_kirim.add(("rem_start", route))

            # 🔥 Alarm START
            if sekarang == start and ("start", route) not in sudah_kirim:
                kirim(f"🔔 START LOADING\n{route}\nJam {start}")
                sudah_kirim.add(("start", route))

            # 🔥 Reminder H-10 SELESAI
            waktu_selesai_minus = (
                datetime.strptime(selesai, "%H:%M") - timedelta(minutes=10)
            ).strftime("%H:%M")

            if sekarang == waktu_selesai_minus and ("rem_end", route) not in sudah_kirim:
                kirim(f"⏰ H-10 SELESAI LOADING\n{route}\nJam {selesai}")
                sudah_kirim.add(("rem_end", route))

            # 🔥 Alarm SELESAI
            if sekarang == selesai and ("end", route) not in sudah_kirim:
                kirim(f"✅ SELESAI LOADING\n{route}\nJam {selesai}")
                sudah_kirim.add(("end", route))

    time.sleep(30)
