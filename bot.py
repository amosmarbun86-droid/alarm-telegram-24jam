import csv
import time
import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# =============================
# KONFIGURASI
# =============================
BOT_TOKEN = "8526408120:AAHqYHx3n9V3qpAqbp8_UDwfWed5SHC7Wbo"
CHAT_ID = "8559067633"
CSV_FILE = "jadwal.csv"

sent_today = set()

# =============================
# KIRIM TELEGRAM
# =============================
def kirim(pesan):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": pesan}
    requests.post(url, data=data)

# =============================
# BACA CSV
# =============================
def baca_jadwal():
    jadwal = []
    with open(CSV_FILE, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            route = r.get("Route", "Tanpa Nama").strip()
            start = r.get("Start Loading", "").strip()
            selesai = r.get("Selesai Loading", "").strip()

            if start:
                jadwal.append(("START", route, start))

            if selesai:
                jadwal.append(("SELESAI", route, selesai))

    return jadwal

# =============================
# LOOP UTAMA
# =============================
print("🚀 BOT ALARM AKTIF (WIB)")

while True:
    now_dt = datetime.now(ZoneInfo("Asia/Jakarta"))
    now = now_dt.strftime("%H:%M")

    try:
        data = baca_jadwal()

        for jenis, route, waktu in data:

            key = (jenis, route, waktu, now_dt.date())

            # 🔔 ALARM TEPAT WAKTU
            if now == waktu and key not in sent_today:
                kirim(f"🔔 {jenis} LOADING\n📍 {route}\n⏰ {waktu} WIB")
                sent_today.add(key)

            # ⏳ REMINDER H-10 MENIT
            t_jadwal = datetime.strptime(waktu, "%H:%M").replace(
                year=now_dt.year,
                month=now_dt.month,
                day=now_dt.day,
                tzinfo=ZoneInfo("Asia/Jakarta"),
            )

            if t_jadwal - timedelta(minutes=10) <= now_dt < t_jadwal:
                key_reminder = ("REMINDER", jenis, route, waktu, now_dt.date())
                if key_reminder not in sent_today:
                    kirim(f"⏳ H-10 MENIT {jenis}\n📍 {route}\n⏰ {waktu} WIB")
                    sent_today.add(key_reminder)

    except Exception as e:
        print("ERROR:", e)

    time.sleep(30)
