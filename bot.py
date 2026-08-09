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
DASHBOARD_PASSWORD = os.getenv("DASHBOARD_PASSWORD")
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
<th>Status</th>
<th>Aksi</th>
</tr>

{% for r in rows %}
<tr style="background-color: {{ route_colors.get(r[0], '#FFFFFF') }};">
<td>{{r[0]}}</td>
<td>{{r[1]}}</td>
<td>{{r[2]}}</td>
<td>
{% if status_list[loop.index0] == "proses" %}
<b style="color:orange;">🟡 Sedang Proses</b>
{% elif status_list[loop.index0] == "selesai" %}
<b style="color:green;">✅ Selesai</b>
{% endif %}
</td>
<td>
<a href="/?edit={{loop.index0}}">Edit</a>
&nbsp;|&nbsp;
<form method="post" style="display:inline">
<input type="hidden" name="action" value="delete">
<input type="hidden" name="index" value="{{loop.index0}}">
<input type="password" name="password" placeholder="password" style="width:90px">
<button type="submit" onclick="return confirm('Yakin hapus baris ini?')">Hapus</button>
</form>
</td>
</tr>
{% endfor %}
</table>

<h3>{{ "Edit Jadwal" if edit_index is not none else "Tambah Jadwal" }}</h3>

{% if error %}
<p style="color:red;">{{ error }}</p>
{% endif %}

<form method="post">
<input type="hidden" name="action" value="{{ 'update' if edit_index is not none else 'add' }}">
{% if edit_index is not none %}
<input type="hidden" name="index" value="{{ edit_index }}">
{% endif %}
Route:<br>
<input name="route" value="{{ edit_route or '' }}"><br>
Start (HH:MM):<br>
<input name="start" value="{{ edit_start or '' }}"><br>
Selesai (HH:MM):<br>
<input name="selesai" value="{{ edit_selesai or '' }}"><br>
Password:<br>
<input type="password" name="password"><br><br>
<button type="submit">{{ "Update" if edit_index is not none else "Tambah" }}</button>
{% if edit_index is not none %}
&nbsp;<a href="/">Batal</a>
{% endif %}
</form>
"""

def baca_rows():
    rows = []
    if os.path.exists(CSV_FILE):
        with open(CSV_FILE, newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            next(reader, None)
            for r in reader:
                rows.append(r)
    return rows

def tulis_rows(rows):
    with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Route","Start Loading","Selesai loading"])
        for r in rows:
            writer.writerow(r)

# Palet warna pastel (24 warna) - cukup terang agar teks hitam tetap terbaca
WARNA_PALET = [
    "#FFD6D6", "#D6FFD6", "#D6E5FF", "#FFF3C4", "#E5D6FF",
    "#D6FFF3", "#FFD6EC", "#E8FFD6", "#D6F0FF", "#FFE0C4",
    "#F0D6FF", "#D6FFE0", "#FFEAA7", "#C4E5FF", "#FFC4D6",
    "#D6FFC4", "#C4FFEA", "#FFC4F0", "#F0FFC4", "#C4D6FF",
    "#FFDAB9", "#C4FFD6", "#E0C4FF", "#FFF0C4",
]

def hitung_route_colors(rows):
    """Kembalikan dict {nama_route: kode_warna}. Route yang sama (nama persis sama)
    selalu dapat warna yang sama, route berbeda dapat warna berbeda, urut
    berdasarkan kemunculan pertama di data."""
    route_colors = {}
    for r in rows:
        if not r:
            continue
        nama_route = r[0]
        if nama_route not in route_colors:
            warna = WARNA_PALET[len(route_colors) % len(WARNA_PALET)]
            route_colors[nama_route] = warna
    return route_colors

def hitung_status_list(rows):
    """Kembalikan list string per baris: 'proses', 'selesai', atau '' (belum mulai/menunggu).
    Menangani jadwal yang melewati tengah malam (misal Start 23:40, Selesai 00:20).

    Aturan:
    - Jadwal normal (Start <= Selesai, dalam hari yang sama):
        sebelum Start        -> '' (menunggu)
        Start s.d. Selesai    -> 'proses'
        setelah Selesai       -> 'selesai'
    - Jadwal lewat tengah malam (Start > Selesai):
        antara Start s.d. tengah malam, atau tengah malam s.d. Selesai -> 'proses'
        setelah Selesai s.d. sebelum Start berikutnya                 -> 'selesai'
    """
    now = datetime.now(ZoneInfo("Asia/Jakarta")).time()
    hasil = []
    for r in rows:
        try:
            start_t = datetime.strptime(r[1].strip(), "%H:%M").time()
            selesai_t = datetime.strptime(r[2].strip(), "%H:%M").time()
        except (ValueError, IndexError):
            hasil.append("")
            continue

        if start_t <= selesai_t:
            if now < start_t:
                status = ""
            elif now <= selesai_t:
                status = "proses"
            else:
                status = "selesai"
        else:
            # rentang melewati tengah malam
            if now >= start_t or now <= selesai_t:
                status = "proses"
            else:
                # sudah lewat Selesai (pagi/siang), menunggu Start malam berikutnya
                status = "selesai"

        hasil.append(status)
    return hasil

@app.route("/", methods=["GET","POST"])
def dashboard():
    if request.method == "POST":
        action = request.form.get("action", "add")
        password = request.form.get("password", "")
        rows = baca_rows()
        error = None
        edit_index = None

        if not DASHBOARD_PASSWORD:
            error = "Password server belum diset (DASHBOARD_PASSWORD kosong). Aksi dinonaktifkan."
        elif password != DASHBOARD_PASSWORD:
            error = "Password salah. Tidak ada perubahan data."
        else:
            if action == "add":
                route = request.form.get("route", "")
                start = request.form.get("start", "")
                selesai = request.form.get("selesai", "")
                rows.append([route, start, selesai])
                tulis_rows(rows)
                return redirect("/")

            elif action == "update":
                try:
                    idx = int(request.form.get("index", "-1"))
                except ValueError:
                    idx = -1

                if 0 <= idx < len(rows):
                    route = request.form.get("route", "")
                    start = request.form.get("start", "")
                    selesai = request.form.get("selesai", "")
                    rows[idx] = [route, start, selesai]
                    tulis_rows(rows)
                    return redirect("/")
                else:
                    error = "Data tidak ditemukan (mungkin sudah diubah)."

            elif action == "delete":
                try:
                    idx = int(request.form.get("index", "-1"))
                except ValueError:
                    idx = -1

                if 0 <= idx < len(rows):
                    rows.pop(idx)
                    tulis_rows(rows)
                    return redirect("/")
                else:
                    error = "Data tidak ditemukan (mungkin sudah diubah)."

        return render_template_string(
            HTML, rows=rows, status_list=hitung_status_list(rows),
            route_colors=hitung_route_colors(rows), error=error,
            edit_index=None, edit_route=None, edit_start=None, edit_selesai=None
        )

    # GET
    rows = baca_rows()
    edit_index = None
    edit_route = edit_start = edit_selesai = None

    edit_param = request.args.get("edit")
    if edit_param is not None:
        try:
            idx = int(edit_param)
        except ValueError:
            idx = -1
        if 0 <= idx < len(rows):
            edit_index = idx
            edit_route, edit_start, edit_selesai = rows[idx]

    return render_template_string(
        HTML, rows=rows, status_list=hitung_status_list(rows),
        route_colors=hitung_route_colors(rows), error=None,
        edit_index=edit_index, edit_route=edit_route,
        edit_start=edit_start, edit_selesai=edit_selesai
    )

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
