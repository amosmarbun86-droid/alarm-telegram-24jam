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
FIREBASE_DB_URL = os.getenv("FIREBASE_DB_URL", "").rstrip("/")
CSV_FILE = "jadwal.csv"  # hanya dipakai untuk migrasi data lama (sekali saja) ke Firebase

sent_today = set()
today_date = None
last_update = None

# ========================
# FLASK DASHBOARD WEB
# ========================
app = Flask(__name__)

HTML = """
<h2>Dashboard Jadwal Route</h2>

{% if not firebase_ready %}
<p style="color:red;"><b>FIREBASE_DB_URL belum diset di Environment Variables.</b> Dashboard tidak bisa membaca/menyimpan data.</p>
{% endif %}

<table border=1>
<tr>
<th>Route</th>
<th>Slot</th>
<th>Start</th>
<th>Selesai</th>
<th>Status</th>
<th>Aksi</th>
</tr>

{% for key, r in rows %}
<tr style="background-color: {{ warna_baris[loop.index0] }};">
<td>{{r[0]}}</td>
<td>{{r[1]}}</td>
<td>{{r[2]}}</td>
<td>{{r[3]}}</td>
<td>
{% if status_list[loop.index0] == "proses" %}
<b style="color:orange;">🟡 Sedang Proses</b>
{% elif status_list[loop.index0] == "selesai" %}
<b style="color:green;">✅ Selesai</b>
{% endif %}
</td>
<td>
<a href="/?edit={{ key }}">Edit</a>
&nbsp;|&nbsp;
<form method="post" style="display:inline">
<input type="hidden" name="action" value="delete">
<input type="hidden" name="key" value="{{ key }}">
<input type="password" name="password" placeholder="password" style="width:90px">
<button type="submit" onclick="return confirm('Yakin hapus baris ini?')">Hapus</button>
</form>
</td>
</tr>
{% endfor %}
</table>

<h3>{{ "Edit Jadwal" if edit_key else "Tambah Jadwal" }}</h3>

{% if error %}
<p style="color:red;">{{ error }}</p>
{% endif %}

<form method="post">
<input type="hidden" name="action" value="{{ 'update' if edit_key else 'add' }}">
{% if edit_key %}
<input type="hidden" name="key" value="{{ edit_key }}">
{% endif %}
Route:<br>
<input name="route" value="{{ edit_route or '' }}"><br>
Slot:<br>
<input name="slot" value="{{ edit_slot or '' }}"><br>
Start (HH:MM):<br>
<input name="start" value="{{ edit_start or '' }}"><br>
Selesai (HH:MM):<br>
<input name="selesai" value="{{ edit_selesai or '' }}"><br>
Password:<br>
<input type="password" name="password"><br><br>
<button type="submit">{{ "Update" if edit_key else "Tambah" }}</button>
{% if edit_key %}
&nbsp;<a href="/">Batal</a>
{% endif %}
</form>
"""

# ========================
# FIREBASE HELPERS (Realtime Database via REST API)
# ========================
def fb_url(path):
    return f"{FIREBASE_DB_URL}/{path}.json"

def fb_get(path):
    if not FIREBASE_DB_URL:
        return None
    try:
        r = requests.get(fb_url(path), timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print("FIREBASE GET ERROR:", e)
        return None

def fb_post(path, data):
    if not FIREBASE_DB_URL:
        return None
    try:
        r = requests.post(fb_url(path), json=data, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print("FIREBASE POST ERROR:", e)
        return None

def fb_put(path, data):
    if not FIREBASE_DB_URL:
        return None
    try:
        r = requests.put(fb_url(path), json=data, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print("FIREBASE PUT ERROR:", e)
        return None

def fb_delete(path):
    if not FIREBASE_DB_URL:
        return False
    try:
        r = requests.delete(fb_url(path), timeout=10)
        r.raise_for_status()
        return True
    except Exception as e:
        print("FIREBASE DELETE ERROR:", e)
        return False

# ========================
# DATA JADWAL (Firebase Realtime Database)
# Struktur tiap entri: {"route":..., "slot":..., "start":..., "selesai":...}
# ========================
def baca_rows():
    """Kembalikan list of (key, [route, slot, start, selesai]) terurut sesuai
    urutan dibuat (push key Firebase terurut kronologis)."""
    data = fb_get("jadwal")
    if not data:
        return []
    hasil = []
    for key in sorted(data.keys()):
        item = data[key] or {}
        route = item.get("route", "")
        slot = item.get("slot", "")
        start = item.get("start", "")
        selesai = item.get("selesai", "")
        hasil.append((key, [route, slot, start, selesai]))
    return hasil

def tambah_row(route, slot, start, selesai):
    return fb_post("jadwal", {"route": route, "slot": slot, "start": start, "selesai": selesai})

def update_row(key, route, slot, start, selesai):
    return fb_put(f"jadwal/{key}", {"route": route, "slot": slot, "start": start, "selesai": selesai})

def hapus_row(key):
    return fb_delete(f"jadwal/{key}")

def migrasi_csv_ke_firebase():
    """Migrasi satu kali: kalau data Firebase masih kosong dan file CSV lama
    ada, pindahkan isinya ke Firebase (slot dikosongkan, diisi manual belakangan)."""
    if not FIREBASE_DB_URL:
        print("⚠️  FIREBASE_DB_URL belum diset, migrasi dilewati.")
        return

    existing = fb_get("jadwal")
    if existing:
        print("Data sudah ada di Firebase, migrasi dilewati.")
        return
    if not os.path.exists(CSV_FILE):
        return

    print("Migrasi data dari jadwal.csv ke Firebase...")
    jumlah = 0
    with open(CSV_FILE, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader, None)
        for r in reader:
            if len(r) >= 3:
                tambah_row(r[0], "", r[1], r[2])
                jumlah += 1
    print(f"Migrasi selesai: {jumlah} rute dipindahkan ke Firebase.")

# Palet warna (24 warna, hue tersebar merata di roda warna) - dibuat jelas beda-beda
# agar mudah dibedakan mata, tapi tetap cukup terang supaya teks hitam terbaca
WARNA_PALET = [
    "#E68989", "#E6A089", "#E6B789", "#E6CE89", "#E6E689",
    "#CEE689", "#B7E689", "#A0E689", "#89E689", "#89E6A0",
    "#89E6B7", "#89E6CE", "#89E6E6", "#89CEE6", "#89B7E6",
    "#89A0E6", "#8989E6", "#A089E6", "#B789E6", "#CE89E6",
    "#E689E6", "#E689CE", "#E689B7", "#E689A0",
]

# Warna khusus untuk rute yang cuma punya 1 slot per hari (disamakan supaya tidak terlalu ramai)
WARNA_SATU_SLOT = "#D3D3D3"  # abu-abu netral, beda dari warna-warna rute di palet

def hitung_warna_baris(rows):
    """rows: list [route, slot, start, selesai]. Kembalikan list warna (1 warna per baris, urut sesuai rows).

    Aturan (berdasarkan RUTE, bukan angka Slot):
    - Rute yang cuma muncul 1x (1 slot per hari)      -> warna abu-abu seragam (WARNA_SATU_SLOT)
    - Rute yang muncul lebih dari 1x (>1 slot per hari) -> semua baris rute itu (termasuk yang
      label Slot-nya "1") dapat SATU warna yang sama dari palet, beda dari rute lain
    """
    from collections import Counter
    jumlah_per_route = Counter(r[0] for r in rows if r)

    # hitung mapping warna rute HANYA untuk rute yang muncul >1 kali (>1 slot per hari)
    route_colors = {}
    for r in rows:
        if not r:
            continue
        nama_route = r[0]
        if jumlah_per_route[nama_route] > 1 and nama_route not in route_colors:
            warna = WARNA_PALET[len(route_colors) % len(WARNA_PALET)]
            route_colors[nama_route] = warna

    hasil = []
    for r in rows:
        if not r:
            hasil.append("#FFFFFF")
            continue
        nama_route = r[0]
        if jumlah_per_route[nama_route] > 1:
            hasil.append(route_colors[nama_route])
        else:
            hasil.append(WARNA_SATU_SLOT)
    return hasil

def hitung_status_list(rows):
    """rows: list [route, slot, start, selesai]. Kembalikan list string per baris:
    'proses', 'selesai', atau '' (belum mulai/menunggu)."""
    now = datetime.now(ZoneInfo("Asia/Jakarta")).time()
    hasil = []
    for r in rows:
        try:
            start_t = datetime.strptime(r[2].strip(), "%H:%M").time()
            selesai_t = datetime.strptime(r[3].strip(), "%H:%M").time()
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
            if now >= start_t or now <= selesai_t:
                status = "proses"
            else:
                status = "selesai"

        hasil.append(status)
    return hasil

@app.route("/", methods=["GET","POST"])
def dashboard():
    firebase_ready = bool(FIREBASE_DB_URL)

    if request.method == "POST":
        action = request.form.get("action", "add")
        password = request.form.get("password", "")
        rows = baca_rows()
        just_rows = [v for k, v in rows]
        error = None

        if not firebase_ready:
            error = "FIREBASE_DB_URL belum diset. Aksi dinonaktifkan."
        elif not DASHBOARD_PASSWORD:
            error = "Password server belum diset (DASHBOARD_PASSWORD kosong). Aksi dinonaktifkan."
        elif password != DASHBOARD_PASSWORD:
            error = "Password salah. Tidak ada perubahan data."
        else:
            if action == "add":
                route = request.form.get("route", "")
                slot = request.form.get("slot", "")
                start = request.form.get("start", "")
                selesai = request.form.get("selesai", "")
                tambah_row(route, slot, start, selesai)
                return redirect("/")

            elif action == "update":
                key = request.form.get("key", "")
                if key:
                    route = request.form.get("route", "")
                    slot = request.form.get("slot", "")
                    start = request.form.get("start", "")
                    selesai = request.form.get("selesai", "")
                    update_row(key, route, slot, start, selesai)
                    return redirect("/")
                else:
                    error = "Data tidak ditemukan (mungkin sudah diubah)."

            elif action == "delete":
                key = request.form.get("key", "")
                if key:
                    hapus_row(key)
                    return redirect("/")
                else:
                    error = "Data tidak ditemukan (mungkin sudah diubah)."

        return render_template_string(
            HTML, rows=rows, status_list=hitung_status_list(just_rows),
            warna_baris=hitung_warna_baris(just_rows), error=error,
            firebase_ready=firebase_ready,
            edit_key=None, edit_route=None, edit_slot=None, edit_start=None, edit_selesai=None
        )

    # GET
    rows = baca_rows()
    just_rows = [v for k, v in rows]
    edit_key = None
    edit_route = edit_slot = edit_start = edit_selesai = None

    edit_param = request.args.get("edit")
    if edit_param:
        for k, v in rows:
            if k == edit_param:
                edit_key = k
                edit_route, edit_slot, edit_start, edit_selesai = v
                break

    return render_template_string(
        HTML, rows=rows, status_list=hitung_status_list(just_rows),
        warna_baris=hitung_warna_baris(just_rows), error=None,
        firebase_ready=firebase_ready,
        edit_key=edit_key, edit_route=edit_route, edit_slot=edit_slot,
        edit_start=edit_start, edit_selesai=edit_selesai
    )

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

Thread(target=run_web).start()
migrasi_csv_ke_firebase()

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
# BACA DATA JADWAL UNTUK SISTEM ALARM (sumber: Firebase)
# ========================
def baca_data_alarm():
    """Kembalikan list tuple (jenis, route, slot, waktu) dari data Firebase."""
    data = []
    for key, r in baca_rows():
        route, slot, start, selesai = r
        start_fmt = format_waktu(start)
        selesai_fmt = format_waktu(selesai)

        if start_fmt:
            data.append(("START", route, slot, start_fmt))
        if selesai_fmt:
            data.append(("SELESAI", route, slot, selesai_fmt))

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
                data = baca_data_alarm()
                if not data:
                    kirim("Jadwal kosong")
                else:
                    msg_text = "📋 JADWAL ROUTE\n\n"
                    for jenis, route, slot, waktu in data:
                        slot_text = f" | Slot {slot}" if slot else ""
                        msg_text += f"{jenis} | {route}{slot_text} | {waktu}\n"
                    kirim(msg_text)

            elif "reload" in text:
                kirim("♻️ Data berhasil di reload dari Firebase")

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

    data = baca_data_alarm()

    for jenis, route, slot, waktu in data:
        try:
            jam_alarm = datetime.strptime(waktu, "%H:%M").replace(
                year=now_dt.year,
                month=now_dt.month,
                day=now_dt.day,
                tzinfo=ZoneInfo("Asia/Jakarta"),
            )

            slot_line = f"\n🔢 Slot {slot}" if slot else ""

            key = (jenis, route, waktu, now_dt.date())

            selisih = abs((now_dt - jam_alarm).total_seconds())
            if selisih <= 30 and key not in sent_today:
                kirim(f"🔔 {jenis} LOADING\n📍 {route}{slot_line}\n⏰ {waktu} WIB")
                sent_today.add(key)

            reminder_time = jam_alarm - timedelta(minutes=10)
            selisih_r = abs((now_dt - reminder_time).total_seconds())
            key_r = ("REMINDER", jenis, route, waktu, now_dt.date())

            if selisih_r <= 30 and key_r not in sent_today:
                kirim(f"⏳ H-10 MENIT {jenis}\n📍 {route}{slot_line}\n⏰ {waktu} WIB")
                sent_today.add(key_r)

        except Exception as e:
            print("ALARM ERROR:", e)

# MAIN LOOP
print("🚀 BOT ROUTE ALARM AKTIF", datetime.now())

while True:
    try:
        cek_command()
        cek_alarm()
    except Exception as e:
        print("CRASH:", e)
        time.sleep(5)

    time.sleep(1)
