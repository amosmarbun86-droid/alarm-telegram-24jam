import csv
import time
import requests
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from flask import Flask, request, redirect, render_template_string
from threading import Thread

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
# FLASK DASHBOARD WEB
# ========================
app = Flask(__name__)

HTML = """
<h2>Dashboard Jadwal Route</h2>

<table border=1>
<tr>
<th>Route</th>
<th>Start</th>
<th>Selesai</th>
</tr>

{% for r in rows %}
<tr>
<td>{{r[0]}}</td>
<td>{{r[1]}}</td>
<td>{{r[2]}}</td>
</tr>
{% endfor %}
</table>

<h3>Tambah Jadwal</h3>

<form method="post">
Route:<br>
<input name="route"><br>
Start (HH:MM):<br>
<input name="start"><br>
Selesai (HH:MM):<br>
<input name="selesai"><br><br>
<button type="submit">Tambah</button>
</form>
"""

@app.route("/", methods=["GET","POST"])
def dashboard():
    if request.method == "POST":
        route = request.form["route"]
        start = request.form["start"]
        selesai = request.form["selesai"]

        file_exists = os.path.exists(CSV_FILE)

        with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(["Route","Start Loading","Selesai loading"])
            writer.writerow([route,start,selesai])

        return redirect("/")

    rows=[]
    if os.path.exists(CSV_FILE):
        with open(CSV_FILE, newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            next(reader, None)
            for r in reader:
                rows.append(r)

    return render_template_string(HTML, rows=rows)

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

Thread(target=run_web).start()

# ========================
# MENU TELEGRAM
# ========================
def menu():
    keyboard = {
        "keyboard": [
            [{"text": "📊 STATUS"}, {"text": "📋 JADWAL"}],
            [{"text": "🔔 TEST"}, {"text": "♻️ RELOAD"}]
        ],
        "resize_keyboard": True
    }
    kirim("📌 MENU UTAMA", keyboard)

# ========================
# SEND TELEGRAM
# ========================
def kirim(text, keyboard=None):
    try:
        payload = {
            "chat_id": CHAT_ID,
            "text": text,
        }

        if keyboard:
            payload["reply_markup"] = keyboard

        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json=payload,
            timeout=10
        )
    except Exception as e:
        print("SEND ERROR:", e)

# ========================
# FORMAT WAKTU
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
            reader.fieldnames = [h.strip() for h in reader.fieldnames]

            for row in reader:
                row = {k.strip(): (v.strip() if v else "") for k, v in row.items()}

                route = row.get("Route") or row.get("route") or row.get("Rute") or ""
                start = row.get("Start Loading") or row.get("start") or ""
                selesai = row.get("Selesai loading") or row.get("selesai") or ""

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
        if not r.get("ok"):
            return

        for u in r.get("result", []):
            last_update = u["update_id"]

            if "message" not in u:
                continue

            msg = u["message"]
            text = msg.get("text", "")
            if text:
                text = text.lower().strip()

            chat = str(msg["chat"]["id"])
            if chat != CHAT_ID:
                continue

            if "/start" in text:
                menu()
                continue

            if "status" in text:
                kirim(f"✅ BOT AKTIF\n{datetime.now().strftime('%H:%M:%S')}")

            elif "test" in text:
                kirim(f"🔔 TEST ALARM\n⏰ {datetime.now().strftime('%H:%M')}")

            elif "jadwal" in text:
                data = baca_csv()
                if not data:
                    kirim("Jadwal kosong")
                else:
                    msg_text = "📋 JADWAL ROUTE\n\n"
                    for jenis, route, waktu in data:
                        msg_text += f"{jenis} | {route} | {waktu}\n"
                    kirim(msg_text)

            elif "reload" in text:
                kirim("♻️ CSV berhasil di reload")

    except Exception as e:
        print("COMMAND ERROR:", e)

# ========================
# ALARM SYSTEM
# ========================
def cek_alarm():
    global today_date

    now_dt = datetime.now(ZoneInfo("Asia/Jakarta"))

    if today_date != now_dt.date():
        sent_today.clear()
        today_date = now_dt.date()

    data = baca_csv()

    for jenis, route, waktu in data:
        try:
            jam_alarm = datetime.strptime(waktu, "%H:%M").replace(
                year=now_dt.year,
                month=now_dt.month,
                day=now_dt.day,
                tzinfo=ZoneInfo("Asia/Jakarta"),
            )

            key = (jenis, route, waktu, now_dt.date())

            selisih = abs((now_dt - jam_alarm).total_seconds())
            if selisih <= 30 and key not in sent_today:
                kirim(f"🔔 {jenis} LOADING\n📍 {route}\n⏰ {waktu} WIB")
                sent_today.add(key)

            reminder_time = jam_alarm - timedelta(minutes=10)
            selisih_r = abs((now_dt - reminder_time).total_seconds())
            key_r = ("REMINDER", jenis, route, waktu, now_dt.date())

            if selisih_r <= 30 and key_r not in sent_today:
                kirim(f"⏳ H-10 MENIT {jenis}\n📍 {route}\n⏰ {waktu} WIB")
                sent_today.add(key_r)

        except Exception as e:
            print("ALARM ERROR:", e)

# ========================
# MAIN LOOP
# ========================
print("🚀 BOT ROUTE ALARM AKTIF", datetime.now())

while True:
    try:
        cek_command()
        cek_alarm()
    except Exception as e:
        print("CRASH:", e)
        time.sleep(5)

    time.sleep(1)
