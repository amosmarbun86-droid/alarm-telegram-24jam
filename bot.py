import csv
import time
import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

BOT_TOKEN = "8526408120:AAHqYHx3n9V3qpAqbp8_UDwfWed5SHC7Wbo"
CHAT_ID = "8559067633"
CSV_FILE = "jadwal.csv"

sent_today = set()


def kirim(pesan):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": pesan})


# =============================
# AMBIL NAMA ROUTE OTOMATIS
# =============================
def ambil_route(row):
    for k in row.keys():
        if k.lower().strip() in ["route", "rute", "tujuan", "jalur"]:
            return row[k].strip()

    return list(row.values())[0].strip()


# =============================
# AMBIL WAKTU DENGAN NAMA FLEKSIBEL
# =============================
def ambil_waktu(row, tipe):
    for k in row.keys():
        key = k.lower().strip()

        if tipe == "start" and "start" in key:
            return row[k].strip()

        if tipe == "selesai" and "selesai" in key:
            return row[k].strip()

    return ""


# =============================
# BACA CSV
# =============================
def baca_jadwal():
    jadwal = []

    with open(CSV_FILE, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for r in reader:
            route = ambil_route(r)

            start = ambil_waktu(r, "start")
            selesai = ambil_waktu(r, "selesai")

            if start:
                jadwal.append(("START", route, start))

            if selesai:
                jadwal.append(("SELESAI", route, selesai))

    return jadwal


# =============================
# LOOP UTAMA
# =============================
print("🚀 BOT ALARM AKTIF 24 JAM (WIB)")

while True:
    now_dt = datetime.now(ZoneInfo("Asia/Jakarta"))
    now = now_dt.strftime("%H:%M")

    try:
        data = baca_jadwal()

        for jenis, route, waktu in data:

            key = (jenis, route, waktu, now_dt.date())

            # 🔔 TEPAT WAKTU
            if now == waktu and key not in sent_today:
                kirim(f"🔔 {jenis} LOADING\n📍 {route}\n⏰ {waktu} WIB")
                sent_today.add(key)

            # ⏳ H-10 MENIT
            t_jadwal = datetime.strptime(waktu, "%H:%M").replace(
                year=now_dt.year,
                month=now_dt.month,
                day=now_dt.day,
                tzinfo=ZoneInfo("Asia/Jakarta"),
            )

            if t_jadwal - timedelta(minutes=10) <= now_dt < t_jadwal:
                key_r = ("REMINDER", jenis, route, waktu, now_dt.date())

                if key_r not in sent_today:
                    kirim(
                        f"⏳ H-10 MENIT {jenis}\n📍 {route}\n⏰ {waktu} WIB"
                    )
                    sent_today.add(key_r)

    except Exception as e:
        print("ERROR:", e)

    time.sleep(30)
