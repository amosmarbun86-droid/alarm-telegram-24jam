import csv
import time
import requests
import os
import base64
import urllib.parse
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from flask import Flask, request, redirect, render_template_string, Response
from threading import Thread
from announcer import buat_pengumuman, latest_announcement, ALARM_SOUND_URL

# ========================
# CONFIG
# ========================
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
DASHBOARD_PASSWORD = os.getenv("DASHBOARD_PASSWORD")
FIREBASE_DB_URL = os.getenv("FIREBASE_DB_URL", "").rstrip("/")
CSV_FILE = "jadwal.csv"  # hanya dipakai untuk migrasi data lama (sekali saja) ke Firebase

# ========================
# PWA: ICON (base64 PNG, tertanam langsung di kode - tidak perlu file terpisah)
# ========================
ICON_192_B64 = "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"
ICON_512_B64 = "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"

sent_today = set()
today_date = None
last_update = None

# ========================
# FLASK DASHBOARD WEB
# ========================
app = Flask(__name__)

HTML = """
<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Dashboard Jadwal Route</title>

<link rel="manifest" href="/manifest.json">
<meta name="theme-color" content="#1C1C1E">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="Alarm 24 Jam">
<link rel="icon" href="/icon-192.png">
<link rel="apple-touch-icon" href="/icon-192.png">

<style>
body { font-family: sans-serif; background:#f4f4f4; margin:0; padding:12px; }
table { border-collapse: collapse; width:100%; background:white; }
th, td { padding:6px 8px; font-size:14px; }
</style>

<script>
if ('serviceWorker' in navigator) {
  window.addEventListener('load', function() {
    navigator.serviceWorker.register('/service-worker.js');
  });
}
</script>
</head>
<body>

<h2>Dashboard Jadwal Route</h2>

<button id="aktifkanSuara" style="padding:8px 16px; margin-bottom:10px;">🔊 Aktifkan Suara Pengumuman</button>
<div id="pengumumanText" style="margin-bottom:10px; font-weight:bold; color:#2E7D32;"></div>
<audio id="audioPlayer"></audio>

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
<th>Sandar</th>
<th>Aksi</th>
</tr>
</table>

<div id="tabelWrap">
{{ tabel_html|safe }}
</div>

<script>
let lastAnnouncementId = null;
let suaraAktif = false;
let sudahInit = false;

// Pulihkan status "Suara Aktif" supaya tidak hilang tiap kali tabel di-refresh
if (localStorage.getItem('suaraAktif') === '1') {
    suaraAktif = true;
    document.getElementById('aktifkanSuara').textContent = '✅ Suara Aktif';
}

document.getElementById('aktifkanSuara').addEventListener('click', () => {
    suaraAktif = true;
    localStorage.setItem('suaraAktif', '1');
    document.getElementById('aktifkanSuara').textContent = '✅ Suara Aktif';

    // "Buka kunci" elemen audio supaya browser mengizinkan play() otomatis nanti
    // (banyak browser mobile blokir audio yang diputar lewat proses background,
    // walau tombol sudah diklik sebelumnya)
    const player = document.getElementById('audioPlayer');
    player.muted = true;
    player.play().then(() => {
        player.pause();
        player.muted = false;
    }).catch(() => {
        player.muted = false;
    });
});

async function cekPengumuman() {
    try {
        const res = await fetch('/api/latest-announcement');
        const data = await res.json();

        if (!sudahInit) {
            // Baseline pertama kali load - jangan auto-play data LAMA yang sudah ada
            lastAnnouncementId = data.id;
            sudahInit = true;
            if (data.id) {
                document.getElementById('pengumumanText').textContent = data.text;
            }
            return;
        }

        if (data.id && data.id !== lastAnnouncementId) {
            lastAnnouncementId = data.id;
            document.getElementById('pengumumanText').textContent = data.text;

            if (suaraAktif) {
                const player = document.getElementById('audioPlayer');
                // Putar suara alarm dulu, begitu selesai baru lanjut suara pengumuman (TTS)
                player.src = '/static/audio/alarm.wav';
                player.onended = () => {
                    player.onended = null;
                    player.src = data.audio_url;
                    player.play();
                };
                player.play();
            }
        }
    } catch (e) {
        console.error('Polling error:', e);
    }
}

// Update ISI TABEL saja lewat AJAX (BUKAN reload halaman penuh) - supaya izin
// autoplay suara dari browser tidak hilang/direset tiap kali tabel diperbarui.
async function refreshTabel() {
    const tagAktif = document.activeElement.tagName;
    if (tagAktif === 'INPUT' || tagAktif === 'TEXTAREA') {
        return; // lagi ngetik di form, jangan diganggu
    }
    try {
        const params = new URLSearchParams(window.location.search);
        const res = await fetch('/partial-table' + (params.toString() ? '?' + params.toString() : ''));
        const html = await res.text();
        document.getElementById('tabelWrap').innerHTML = html;
    } catch (e) {
        console.error('Refresh tabel error:', e);
    }
}

setInterval(cekPengumuman, 5000);
setInterval(refreshTabel, 30000);
</script>

</body>
</html>
"""

TABEL_HTML = """
<table border=1>
<tr>
<th>Route</th>
<th>Slot</th>
<th>Start</th>
<th>Selesai</th>
<th>Status</th>
<th>Sandar</th>
<th>Aksi</th>
</tr>

{% for key, r in rows %}
<tr style="background-color: {{ warna_baris[loop.index0] }};">
<td>
{% if maps_links[loop.index0] %}
<a href="{{ maps_links[loop.index0] }}" target="_blank" rel="noopener" style="color:#0645AD;">{{r[0]}}</a>
{% else %}
{{r[0]}}
{% endif %}
</td>
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
{% if sandar_list[loop.index0] %}
<b style="color:#2E7D32;">🚛 Sudah Sandar</b><br>
<form method="post" style="display:inline">
<input type="hidden" name="action" value="toggle_sandar">
<input type="hidden" name="key" value="{{ key }}">
<input type="hidden" name="status" value="off">
<input type="password" name="password" placeholder="password" style="width:80px">
<button type="submit">Batalkan</button>
</form>
{% else %}
<form method="post" style="display:inline">
<input type="hidden" name="action" value="toggle_sandar">
<input type="hidden" name="key" value="{{ key }}">
<input type="hidden" name="status" value="on">
<input type="password" name="password" placeholder="password" style="width:80px">
<button type="submit">Tandai Sandar</button>
</form>
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

def fb_patch(path, data):
    """Update sebagian field saja tanpa menghapus field lain yang tidak disebut
    (beda dengan fb_put yang menimpa seluruh objek di path itu)."""
    if not FIREBASE_DB_URL:
        return None
    try:
        r = requests.patch(fb_url(path), json=data, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print("FIREBASE PATCH ERROR:", e)
        return None

# ========================
# DATA JADWAL (Firebase Realtime Database)
# Struktur tiap entri: {"route":..., "slot":..., "start":..., "selesai":..., "sandar_tanggal":...}
# "sandar_tanggal" diisi tanggal (YYYY-MM-DD, WIB) saat operator klik "Sudah Sandar".
# Otomatis dianggap tidak aktif lagi kalau tanggalnya bukan hari ini (reset harian).
# ========================
def baca_rows():
    """Kembalikan list of (key, [route, slot, start, selesai, sandar_tanggal]) terurut sesuai
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
        sandar_tanggal = item.get("sandar_tanggal", "")
        hasil.append((key, [route, slot, start, selesai, sandar_tanggal]))
    return hasil

def tambah_row(route, slot, start, selesai):
    return fb_post("jadwal", {"route": route, "slot": slot, "start": start, "selesai": selesai})

def update_row(key, route, slot, start, selesai):
    # pakai PATCH (bukan PUT) supaya field "sandar_tanggal" yang sudah ada TIDAK ikut terhapus
    return fb_patch(f"jadwal/{key}", {"route": route, "slot": slot, "start": start, "selesai": selesai})

def set_sandar(key, aktif):
    """Tandai/batalkan status 'Sudah Sandar' untuk satu baris."""
    if aktif:
        tanggal = datetime.now(ZoneInfo("Asia/Jakarta")).strftime("%Y-%m-%d")
    else:
        tanggal = ""
    return fb_patch(f"jadwal/{key}", {"sandar_tanggal": tanggal})

def is_sandar_hari_ini(sandar_tanggal):
    """True kalau sandar_tanggal persis hari ini (WIB) - otherwise dianggap sudah reset."""
    if not sandar_tanggal:
        return False
    today_str = datetime.now(ZoneInfo("Asia/Jakarta")).strftime("%Y-%m-%d")
    return sandar_tanggal == today_str

def hitung_sandar_list(rows, status_list):
    """rows: list [route, slot, start, selesai, sandar_tanggal]. status_list: hasil hitung_status_list
    (sejajar urutannya dengan rows). Kembalikan list boolean per baris.

    'Sudah Sandar' otomatis dianggap tidak aktif lagi kalau:
    - tanggal tandanya bukan hari ini (reset harian), ATAU
    - loading rute itu sudah berstatus 'selesai' (otomatis hilang begitu loading kelar)
    """
    hasil = []
    for r, status in zip(rows, status_list):
        aktif = is_sandar_hari_ini(r[4] if len(r) > 4 else "")
        if status == "selesai":
            aktif = False
        hasil.append(aktif)
    return hasil

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

def buat_link_maps(nama_rute):
    """Ubah nama rute (format: 'Siborong - Borong DC > Hub1 - Hub2 - Hub3') jadi link
    Google Maps directions dari Siborong - Borong DC, lewat tiap hub berurutan, sampai hub terakhir.
    Kembalikan None kalau format rute tidak sesuai (tidak ada tanda '>')."""
    if not nama_rute or ">" not in nama_rute:
        return None

    asal_bagian, hub_bagian = nama_rute.split(">", 1)
    asal = asal_bagian.strip()
    hub_list = [h.strip() for h in hub_bagian.strip().split(" - ") if h.strip()]

    if not asal or not hub_list:
        return None

    titik_titik = [asal] + hub_list
    # tambahkan konteks wilayah supaya Google Maps lebih akurat mencocokkan nama hub
    titik_encoded = [urllib.parse.quote(f"{t}, Sumatera Utara") for t in titik_titik]
    return "https://www.google.com/maps/dir/" + "/".join(titik_encoded)

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

# ========================
# PWA: MANIFEST, ICON, SERVICE WORKER
# ========================
@app.route("/manifest.json")
def manifest():
    data = {
        "name": "Alarm Jadwal Loading 24 Jam",
        "short_name": "Alarm24Jam",
        "start_url": "/",
        "scope": "/",
        "display": "standalone",
        "background_color": "#1C1C1E",
        "theme_color": "#1C1C1E",
        "orientation": "portrait",
        "icons": [
            {"src": "/icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any maskable"},
            {"src": "/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any maskable"},
        ],
    }
    import json
    return Response(json.dumps(data), mimetype="application/manifest+json")

@app.route("/icon-192.png")
def icon_192():
    return Response(base64.b64decode(ICON_192_B64), mimetype="image/png")

@app.route("/icon-512.png")
def icon_512():
    return Response(base64.b64decode(ICON_512_B64), mimetype="image/png")

@app.route("/service-worker.js")
def service_worker():
    js = """
self.addEventListener('install', function(event) {
  self.skipWaiting();
});
self.addEventListener('activate', function(event) {
  event.waitUntil(self.clients.claim());
});
self.addEventListener('fetch', function(event) {
  event.respondWith(
    fetch(event.request).catch(function() {
      return new Response('Anda sedang offline.', { status: 503, statusText: 'Offline' });
    })
  );
});
"""
    return Response(js, mimetype="application/javascript")

@app.route("/api/latest-announcement")
def api_latest_announcement():
    from flask import jsonify
    return jsonify(latest_announcement)
    
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

            elif action == "toggle_sandar":
                key = request.form.get("key", "")
                status_baru = request.form.get("status", "on")
                if key:
                    set_sandar(key, status_baru == "on")
                    if status_baru == "on":
                        # Cari nama rute & slot dari data yang sudah dibaca, lalu
                        # trigger pengumuman suara "sudah sandar" untuk rute itu
                        for k, v in rows:
                            if k == key:
                                waktu_sandar = datetime.now(ZoneInfo("Asia/Jakarta")).strftime("%H:%M")
                                buat_pengumuman("SANDAR", v[0], v[1], waktu_sandar)
                                break
                    return redirect("/")
                else:
                    error = "Data tidak ditemukan (mungkin sudah diubah)."

        status_list_hasil = hitung_status_list(just_rows)
        return render_template_string(
            HTML, rows=rows, status_list=status_list_hasil,
            warna_baris=hitung_warna_baris(just_rows),
            sandar_list=hitung_sandar_list(just_rows, status_list_hasil),
            maps_links=[buat_link_maps(r[0]) for r in just_rows], error=error,
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
                edit_route, edit_slot, edit_start, edit_selesai = v[0], v[1], v[2], v[3]
                break

    status_list_hasil = hitung_status_list(just_rows)
    return render_template_string(
        HTML, rows=rows, status_list=status_list_hasil,
        warna_baris=hitung_warna_baris(just_rows),
        sandar_list=hitung_sandar_list(just_rows, status_list_hasil),
        maps_links=[buat_link_maps(r[0]) for r in just_rows], error=None,
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
        route, slot, start, selesai = r[0], r[1], r[2], r[3]
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
                buat_pengumuman(jenis, route, slot, waktu)
                sent_today.add(key)

            if jenis == "START":
                # Reminder 10 menit sebelum mulai loading
                reminder_time = jam_alarm - timedelta(minutes=10)
                selisih_r = abs((now_dt - reminder_time).total_seconds())
                key_r = ("REMINDER", jenis, route, waktu, now_dt.date())

                if selisih_r <= 30 and key_r not in sent_today:
                    kirim(f"⏳ H-10 MENIT {jenis}\n📍 {route}{slot_line}\n⏰ {waktu} WIB")
                    buat_pengumuman("REMINDER", route, slot, waktu)
                    sent_today.add(key_r)

            elif jenis == "SELESAI":
                # Reminder 15 menit sebelum selesai loading
                reminder15_time = jam_alarm - timedelta(minutes=15)
                selisih_15 = abs((now_dt - reminder15_time).total_seconds())
                key_15 = ("REMINDER15", jenis, route, waktu, now_dt.date())

                if selisih_15 <= 30 and key_15 not in sent_today:
                    kirim(f"⏳ H-15 MENIT SELESAI LOADING\n📍 {route}{slot_line}\n⏰ {waktu} WIB")
                    buat_pengumuman("REMINDER_SELESAI", route, slot, waktu)
                    sent_today.add(key_15)

        except Exception as e:
            print("ALARM ERROR:", e)
