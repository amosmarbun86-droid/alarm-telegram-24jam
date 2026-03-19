import csv
import time
import requests
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# ========================
# CONFIG
# ========================

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
CSV_FILE = "jadwal.csv"

sent_today = set()
today_date = None
last_update = None


# ========================
# SEND MESSAGE TELEGRAM
# ========================
def kirim(text):
    try:
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            data={"chat_id": CHAT_ID, "text": text},
        )
    except Exception as e:
        print("SEND ERROR:", e)


# ========================
# FORMAT WAKTU HH:MM
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

            # bersihkan header dari spasi
            reader.fieldnames = [h.strip() for h in reader.fieldnames]

            for row in reader:
                # bersihkan setiap nilai
                row = {k.strip(): (v.strip() if v else "") for k, v in row.items()}

                # cari kemungkinan nama kolom route
                route = (
                    row.get("Route")
                    or row.get("route")
                    or row.get("ROUTE")
                    or row.get("Route Wilayah")
                    or row.get("Rute")
                    or ""
                )

                # kemungkinan nama kolom start
                start = (
                    row.get("Start Loading")
                    or row.get("start")
                    or row.get("Start")
                    or ""
                )

                # kemungkinan nama kolom selesai
                selesai = (
                    row.get("Selesai loading")
                    or row.get("selesai")
                    or row.get("Finish")
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
# CHECK TELEGRAM COMMAND
# ========================
def cek_command():
    global last_update
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
    params = {"timeout": 1}
    if last_update:
        params["offset"] = last_update + 1

    try:
        r = requests.get(url, params=params).json()
        if not r.get("ok"):
            print("Telegram API ERROR:", r)
            return

        for u in r.get("result", []):
            last_update = u["update_id"]

            if "message" not in u:
                continue

            msg = u["message"]

            # DEBUG: lihat isi message
            # print("Incoming message:", msg)

            text = msg.get("text", "")
            if text:
                text = text.lower().strip()

            chat = str(msg["chat"]["id"])
            if chat != CHAT_ID:
                continue  # hanya respon chat ID yang sesuai

            # COMMANDS
            if "/status" in text:
                kirim(f"✅ BOT AKTIF\n{datetime.now().strftime('%H:%M:%S')}")

            elif "/testalarm" in text:
                kirim(
                    f"🔔 TEST ALARM\n📍 TEST ROUTE\n⏰ {datetime.now().strftime('%H:%M')}"
                )

            elif "/jadwal" in text:
                data = baca_csv()
                if not data:
                    kirim("Jadwal kosong")
                    continue
                msg_text = "📋 JADWAL ROUTE\n\n"
                for jenis, route, waktu in data:
                    msg_text += f"{jenis} | {route} | {waktu}\n"
                kirim(msg_text)

            elif "/reload" in text:
                kirim("♻️ CSV berhasil di reload")

            # UPLOAD CSV
            if "document" in msg:
                doc = msg["document"]
                if doc["file_name"].endswith(".csv"):
                    try:
                        file_id = doc["file_id"]
                        r = requests.get(
                            f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}"
                        ).json()
                        path = r["result"]["file_path"]
                        download_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{path}"
                        data = requests.get(download_url).content
                        with open(CSV_FILE, "wb") as f:
                            f.write(data)
                        kirim("✅ CSV berhasil diupload")
                    except Exception as e:
                        kirim(f"❌ ERROR upload CSV: {e}")
                        print("UPLOAD ERROR:", e)

    except Exception as e:
        print("COMMAND ERROR:", e)


# ========================
# CHECK ALARM
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

        # TEPAT WAKTU
        if now == waktu and key not in sent_today:
            pesan = f"🔔 {jenis} LOADING\n📍 {route}\n⏰ {waktu} WIB"
            kirim(pesan)
            print("ALARM:", pesan)
            sent_today.add(key)

        # REMINDER H-10
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
                    pesan = f"⏳ H-10 MENIT {jenis}\n📍 {route}\n⏰ {waktu} WIB"
                    kirim(pesan)
                    print("REMINDER:", pesan)
                    sent_today.add(key_r)
        except:
            pass


# ========================
# MAIN LOOP
# ========================
print("🚀 BOT ROUTE ALARM AKTIF")

while True:
    try:
        cek_command()
        cek_alarm()
    except Exception as e:
        print("CRASH:", e)
        time.sleep(5)
    time.sleep(10)
