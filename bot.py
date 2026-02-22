import csv
import time
import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

BOT_TOKEN = "8526408120:AAHqYHx3n9V3qpAqbp8_UDwfWed5SHC7Wbo"
CHAT_ID = "8559067633"
CSV_FILE = "jadwal.csv"

H10_SOUND = "alarm_h10_warning.wav"
START_SOUND = "alarm_start_loading_industrial.wav"
FINISH_SOUND = "alarm_finish_loading_industrial.wav"

sent_today = set()


def kirim_suara(file_audio, caption):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendAudio"
    with open(file_audio, "rb") as f:
        requests.post(
            url,
            data={"chat_id": CHAT_ID, "caption": caption},
            files={"audio": f},
        )


def ambil_route(row):
    for k in row.keys():
        if k.lower().strip() in ["route", "rute", "tujuan", "jalur"]:
            return row[k].strip()
    return list(row.values())[0].strip()


def ambil_waktu(row, tipe):
    for k in row.keys():
        key = k.lower().strip()

        if tipe == "start" and "start" in key:
            return row[k].strip()

        if tipe == "selesai" and "selesai" in key:
            return row[k].strip()

    return ""


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


print("🚀 BOT ALARM INDUSTRI AKTIF 24 JAM (WIB)")

while True:
    now_dt = datetime.now(ZoneInfo("Asia/Jakarta"))
    now = now_dt.strftime("%H:%M")

    try:
        data = baca_jadwal()

        for jenis, route, waktu in data:

            key = (jenis, route, waktu, now_dt.date())

            t_jadwal = datetime.strptime(waktu, "%H:%M").replace(
                year=now_dt.year,
                month=now_dt.month,
                day=now_dt.day,
                tzinfo=ZoneInfo("Asia/Jakarta"),
            )

            # ⏳ H-10
            if t_jadwal - timedelta(minutes=10) <= now_dt < t_jadwal:
                key_r = ("REMINDER", jenis, route, waktu, now_dt.date())

                if key_r not in sent_today:
                    kirim_suara(
                        H10_SOUND,
                        f"⏳ H-10 MENIT {jenis}\n📍 {route}\n⏰ {waktu} WIB",
                    )
                    sent_today.add(key_r)

            # 🚨 TEPAT WAKTU
            if now == waktu and key not in sent_today:

                caption = f"🚨 {jenis} LOADING\n📍 {route}\n⏰ {waktu} WIB"

                if jenis == "START":
                    kirim_suara(START_SOUND, caption)
                else:
                    kirim_suara(FINISH_SOUND, caption)

                sent_today.add(key)

    except Exception as e:
        print("ERROR:", e)

    time.sleep(30)
