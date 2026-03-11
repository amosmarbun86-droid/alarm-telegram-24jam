import csv
import time
import requests
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

BOT_TOKEN = "8526408120:AAHqYHx3n9V3qpAqbp8_UDwfWed5SHC7Wbo"
CHAT_ID = "ISI_CHAT_ID"
CSV_FILE = "8559067633"

sent_today = set()
today_date = None
last_update = None


# ========================
# TELEGRAM SEND
# ========================
def kirim(text):

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    try:
        requests.post(url, data={
            "chat_id": CHAT_ID,
            "text": text
        })
    except Exception as e:
        print("SEND ERROR:", e)


# ========================
# FORMAT TIME
# ========================
def format_waktu(w):

    try:
        t = datetime.strptime(w.strip(), "%H:%M")
        return t.strftime("%H:%M")
    except:
        return ""


# ========================
# READ CSV
# ========================
def baca_csv():

    data = []

    if not os.path.exists(CSV_FILE):
        return data

    try:

        with open(CSV_FILE, newline="", encoding="utf-8") as f:

            reader = csv.DictReader(f)

            for row in reader:

                route = (
                    row.get("Route")
                    or row.get("route")
                    or ""
                )

                start = (
                    row.get("Start Loading")
                    or row.get("start")
                    or ""
                )

                selesai = (
                    row.get("Selesai loading")
                    or row.get("selesai")
                    or ""
                )

                start = format_waktu(start)
                selesai = format_waktu(selesai)

                if start:
                    data.append(("START", route, start))

                if selesai:
                    data.append(("SELESAI", route, selesai))

    except Exception as e:
        print("CSV ERROR:", e)

    return data


# ========================
# COMMAND TELEGRAM
# ========================

def cek_command():

    global last_update

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"

    params = {"timeout": 1}

    if last_update:
        params["offset"] = last_update + 1

    try:

        r = requests.get(url, params=params).json()

        # cek error telegram API
        if not r.get("ok"):
            print("Telegram API ERROR:", r)
            return

        for u in r.get("result", []):

            last_update = u["update_id"]

            if "message" not in u:
                continue

            msg = u["message"]

            chat = str(msg["chat"]["id"])

            if chat != CHAT_ID:
                continue

            text = msg.get("text", "")

            # =================
            # COMMAND STATUS
            # =================
            if text == "/status":

                kirim(
                    "✅ BOT AKTIF\n"
                    + datetime.now().strftime("%H:%M:%S")
                )

            # =================
            # COMMAND TEST ALARM
            # =================
            elif text == "/testalarm":

                kirim(
                    "🔔 TEST ALARM\n"
                    "📍 TEST ROUTE\n"
                    "⏰ " + datetime.now().strftime("%H:%M")
                )

            # =================
            # COMMAND JADWAL
            # =================
            elif text == "/jadwal":

                data = baca_csv()

                if not data:
                    kirim("Jadwal kosong")
                    continue

                msg_text = "📋 JADWAL ROUTE\n\n"

                for jenis, route, waktu in data:
                    msg_text += f"{jenis} | {route} | {waktu}\n"

                kirim(msg_text)

            # =================
            # COMMAND RELOAD
            # =================
            elif text == "/reload":

                kirim("♻️ CSV berhasil di reload")

            # =================
            # UPLOAD CSV
            # =================
            if "document" in msg:

                doc = msg["document"]

                if doc["file_name"].endswith(".csv"):

                    file_id = doc["file_id"]

                    r = requests.get(
                        f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}"
                    ).json()

                    path = r["result"]["file_path"]

                    download = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{path}"

                    data = requests.get(download).content

                    with open(CSV_FILE, "wb") as f:
                        f.write(data)

                    kirim("✅ CSV berhasil diupload")

    except Exception as e:

        print("COMMAND ERROR:", e)

# ========================
# ALARM CHECK
# ========================
def cek_alarm():

    global today_date

    now_dt = datetime.now(ZoneInfo("Asia/Jakarta"))
    now = now_dt.strftime("%H:%M")

    if today_date != now_dt.date():

        sent_today.clear()
        today_date = now_dt.date()

    data = baca_csv()

    for jenis, route, waktu in data:

        key = (jenis, route, waktu, now_dt.date())

        if now == waktu and key not in sent_today:

            pesan = (
                f"🔔 {jenis} LOADING\n"
                f"📍 {route}\n"
                f"⏰ {waktu} WIB"
            )

            kirim(pesan)

            print("ALARM:", pesan)

            sent_today.add(key)

        try:

            t = datetime.strptime(waktu, "%H:%M").replace(
                year=now_dt.year,
                month=now_dt.month,
                day=now_dt.day,
                tzinfo=ZoneInfo("Asia/Jakarta"),
            )

            if t - timedelta(minutes=10) <= now_dt < t:

                key_r = ("REMINDER", jenis, route, waktu)

                if key_r not in sent_today:

                    pesan = (
                        f"⏳ H-10 MENIT {jenis}\n"
                        f"📍 {route}\n"
                        f"⏰ {waktu} WIB"
                    )

                    kirim(pesan)

                    print("REMINDER:", pesan)

                    sent_today.add(key_r)

        except:
            pass


print("🚀 BOT ROUTE ALARM AKTIF")

while True:

    try:

        cek_command()
        cek_alarm()

    except Exception as e:

        print("CRASH:", e)
        time.sleep(5)

    time.sleep(10)
