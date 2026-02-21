import pandas as pd
import requests
import time
from datetime import datetime, timedelta

TOKEN = "8526408120:AAHqYHx3n9V3qpAqbp8_UDwfWed5SHC7Wbo"
CHAT_ID = "8559067633"

df = pd.read_csv("Jadwal_Route_Siborong_Borong.csv")

sudah_kirim = set()

def kirim(pesan):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": pesan})

print("🔔 BOT LOGISTIK AKTIF 24 JAM")

while True:
    now = datetime.now()

    for i, row in df.iterrows():
        waktu_str = str(row["Start Loading"])[:5]
        jam, menit = map(int, waktu_str.split(":"))

        jadwal = now.replace(hour=jam, minute=menit, second=0, microsecond=0)
        reminder = jadwal - timedelta(minutes=10)

        key_alarm = f"{i}_alarm_{jadwal.date()}"
        key_reminder = f"{i}_reminder_{jadwal.date()}"

        # ⏰ REMINDER H-10 MENIT
        if reminder <= now < jadwal and key_reminder not in sudah_kirim:
            pesan = f"""
⏰ REMINDER 10 MENIT LAGI

Route : {row['Route']}
Slot  : {row['Slot']}

Start Loading : {waktu_str}
"""
            kirim(pesan)
            sudah_kirim.add(key_reminder)

        # 🚛 ALARM UTAMA
        if jadwal <= now < jadwal + timedelta(minutes=1) and key_alarm not in sudah_kirim:
            pesan = f"""
🚛 WAKTUNYA BERANGKAT

Route : {row['Route']}
Slot  : {row['Slot']}

⏰ Start Loading : {waktu_str}
"""
            kirim(pesan)
            sudah_kirim.add(key_alarm)

    time.sleep(20)
