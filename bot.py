import csv
import time
import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import os

BOT_TOKEN ="8526408120:AAHqYHx3n9V3qpAqbp8_UDwfWed5SHC7Wbo"
CHAT_ID ="8559067633"
CSV_FILE = "jadwal.csv"

sent_today = set()
today_date = None
last_update_id = None
mode_tambah = False

# ==========================
# TELEGRAM API
# ==========================
def kirim(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    requests.post(url, data={
        "chat_id": CHAT_ID,
        "text": text
    })


def get_updates():
    global last_update_id

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"

    params = {"timeout": 1}

    if last_update_id:
        params["offset"] = last_update_id + 1

    r = requests.get(url, params=params).json()

    return r["result"]


# ==========================
# CSV FUNCTIONS
# ==========================
def baca_csv():

    data = []

    if not os.path.exists(CSV_FILE):
        return data

    with open(CSV_FILE, newline="", encoding="utf-8") as f:

        reader = csv.DictReader(f)

        for row in reader:

            route = row["Route"]
            start = row["Start Loading"]
            selesai = row["Selesai loading"]

            data.append((route, start, selesai))

    return data


def simpan_csv(data):

    with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:

        writer = csv.writer(f)

        writer.writerow(["Route", "Start Loading", "Selesai loading"])

        for r in data:
            writer.writerow(r)


# ==========================
# FORMAT WAKTU
# ==========================
def format_waktu(w):

    try:
        t = datetime.strptime(w.strip(), "%H:%M")
        return t.strftime("%H:%M")
    except:
        return ""


# ==========================
# TAMPILKAN JADWAL
# ==========================
def kirim_jadwal():

    data = baca_csv()

    if not data:
        kirim("Jadwal kosong")
        return

    text = "📋 DAFTAR JADWAL\n\n"

    for i, d in enumerate(data, 1):

        text += (
            f"{i}. {d[0]}\n"
            f"START : {d[1]}\n"
            f"SELESAI : {d[2]}\n\n"
        )

    kirim(text)


# ==========================
# TAMBAH JADWAL
# ==========================
def tambah_jadwal(text):

    data = baca_csv()

    try:

        route, start, selesai = text.split("|")

        route = route.strip()
        start = format_waktu(start)
        selesai = format_waktu(selesai)

        data.append((route, start, selesai))

        simpan_csv(data)

        kirim("✅ Jadwal berhasil ditambah")

    except:
        kirim("❌ Format salah\nContoh:\nRoute | 01:00 | 02:00")


# ==========================
# HAPUS JADWAL
# ==========================
def hapus_jadwal(n):

    data = baca_csv()

    try:

        n = int(n) - 1

        if n < 0 or n >= len(data):
            kirim("Nomor tidak ada")
            return

        data.pop(n)

        simpan_csv(data)

        kirim("✅ Jadwal dihapus")

    except:
        kirim("Kirim nomor jadwal")


# ==========================
# PROSES COMMAND TELEGRAM
# ==========================
def proses_telegram():

    global last_update_id
    global mode_tambah

    updates = get_updates()

    for u in updates:

        last_update_id = u["update_id"]

        if "message" not in u:
            continue

        msg = u["message"]

        if str(msg["chat"]["id"]) != CHAT_ID:
            continue

        # ==================
        # FILE CSV UPLOAD
        # ==================
        if "document" in msg:

            doc = msg["document"]

            if doc["file_name"].endswith(".csv"):

                file_id = doc["file_id"]

                url = f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}"

                r = requests.get(url).json()

                file_path = r["result"]["file_path"]

                download = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"

                data = requests.get(download).content

                with open(CSV_FILE, "wb") as f:
                    f.write(data)

                kirim("✅ CSV berhasil diupload")

        # ==================
        # TEXT COMMAND
        # ==================
        if "text" not in msg:
            continue

        text = msg["text"]

        if text == "/jadwal":
            kirim_jadwal()

        elif text == "/tambah":

            mode_tambah = True

            kirim(
                "Kirim format:\n"
                "Route | Start | Selesai\n\n"
                "Contoh:\n"
                "Medan DC > Kisaran Hub | 01:00 | 02:00"
            )

        elif text == "/hapus":

            kirim_jadwal()
            kirim("Kirim nomor jadwal yang ingin dihapus")

        elif mode_tambah:

            tambah_jadwal(text)
            mode_tambah = False

        elif text.isdigit():

            hapus_jadwal(text)


# ==========================
# ALARM JADWAL
# ==========================
def cek_alarm():

    global today_date

    now_dt = datetime.now(ZoneInfo("Asia/Jakarta"))
    now = now_dt.strftime("%H:%M")

    if today_date != now_dt.date():
        sent_today.clear()
        today_date = now_dt.date()

    data = baca_csv()

    for route, start, selesai in data:

        for jenis, waktu in [
            ("START", start),
            ("SELESAI", selesai),
        ]:

            waktu = format_waktu(waktu)

            key = (jenis, route, waktu, now_dt.date())

            if now == waktu and key not in sent_today:

                kirim(
                    f"🔔 {jenis} LOADING\n"
                    f"📍 {route}\n"
                    f"⏰ {waktu} WIB"
                )

                sent_today.add(key)

            t_jadwal = datetime.strptime(waktu, "%H:%M").replace(
                year=now_dt.year,
                month=now_dt.month,
                day=now_dt.day,
                tzinfo=ZoneInfo("Asia/Jakarta"),
            )

            if t_jadwal - timedelta(minutes=10) <= now_dt < t_jadwal:

                key_r = ("REMINDER", jenis, route, waktu)

                if key_r not in sent_today:

                    kirim(
                        f"⏳ H-10 MENIT {jenis}\n"
                        f"📍 {route}\n"
                        f"⏰ {waktu} WIB"
                    )

                    sent_today.add(key_r)


# ==========================
# MAIN LOOP
# ==========================
print("🚀 BOT JADWAL AKTIF")

while True:

    try:

        proses_telegram()
        cek_alarm()

    except Exception as e:
        print("ERROR:", e)

    time.sleep(5)
