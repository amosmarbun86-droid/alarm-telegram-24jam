# BOT ALARM LOADING — FINAL (RAPI & SIAP PASTE)
# ==================================================
# ✅ Tanpa suara
# ✅ Tanda warna (emoji) berbeda
# ✅ Ambil Slot dari CSV
# ✅ H‑10 Start & Finish
# ✅ Shift malam otomatis (lewat tengah malam aman)
# ✅ Anti dobel kirim (presisi detik)
# ✅ Reset otomatis tiap hari
# ✅ Timezone WIB (Asia/Jakarta / UTC+7)
# ✅ Siap deploy 24 jam (Railway / VPS)
# ==================================================

import csv
import time
import requests
from datetime import datetime, timedelta, timezone

# ================== KONFIGURASI ==================
TOKEN = "8526408120:AAHqYHx3n9V3qpAqbp8_UDwfWed5SHC7Wbo"     # ← GANTI
CHAT_ID = "8559067633"     # ← GANTI
CSV_FILE = "jadwal.csv"     # Nama file CSV

# Timezone WIB (UTC+7)
WIB = timezone(timedelta(hours=7))


# ================== FUNGSI KIRIM ==================

def kirim(teks: str):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    data = {
        "chat_id": CHAT_ID,
        "text": teks
    }
    requests.post(url, data=data, timeout=20)


# ================== UTIL WAKTU ==================

def now_wib() -> datetime:
    """Waktu sekarang dalam WIB (tanpa microsecond)"""
    return datetime.now(WIB).replace(microsecond=0)


def parse_hhmm_today_wib(hhmm: str, base: datetime) -> datetime:
    """Ubah 'HH:MM' menjadi datetime hari ini (WIB)"""
    h, m = hhmm.strip().split(":")
    return base.replace(hour=int(h), minute=int(m), second=0)


def normalize_shift(t: datetime, base: datetime) -> datetime:
    """
    SHIFT MALAM OTOMATIS
    Jika selisih > 12 jam → geser ke hari terdekat
    """
    diff = (t - base).total_seconds()

    if diff <= -12 * 3600:
        return t + timedelta(days=1)

    if diff >= 12 * 3600:
        return t - timedelta(days=1)

    return t


def due(now: datetime, target: datetime, tol_sec: int = 1) -> bool:
    """
    True jika sekarang tepat di waktu target
    Toleransi ±1 detik (sangat presisi)
    """
    return abs((now - target).total_seconds()) <= tol_sec


# ================== STATE ==================
last_sent = set()           # Simpan event yang sudah dikirim hari ini
current_day = now_wib().date()

print("🚀 BOT ALARM LOADING FINAL AKTIF (WIB • SHIFT MALAM OTOMATIS)")


# ================== LOOP UTAMA ==================
while True:
    now = now_wib()

    # Reset otomatis tiap hari
    if now.date() != current_day:
        last_sent.clear()
        current_day = now.date()

    with open(CSV_FILE, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row in reader:
            route = (row.get("Route") or "-").strip()
            slot = (row.get("Slot") or "-").strip()
            start_s = (row.get("Start Loading") or "").strip()
            finish_s = (row.get("Selesai Loading") or "").strip()

            if not start_s or not finish_s:
                continue

            try:
                t_start = normalize_shift(
                    parse_hhmm_today_wib(start_s, now), now
                )
                t_finish = normalize_shift(
                    parse_hhmm_today_wib(finish_s, now), now
                )
            except Exception:
                continue

            h10_start = t_start - timedelta(minutes=10)
            h10_finish = t_finish - timedelta(minutes=10)

            # ==================================================
            # H‑10 START
            # ==================================================
            key = f"H10S|{route}|{slot}|{start_s}|{current_day}"
            if due(now, h10_start) and key not in last_sent:
                kirim(
                    "🟠 ⏳ H-10 MENIT LOADING\n"
                    "━━━━━━━━━━━━━━━━\n"
                    f"📦 Route : {route}\n"
                    f"🅿️ Slot  : {slot}\n"
                    f"⏰ Jam   : {start_s} WIB\n"
                    "━━━━━━━━━━━━━━━━"
                )
                last_sent.add(key)

            # ==================================================
            # START LOADING
            # ==================================================
            key = f"START|{route}|{slot}|{start_s}|{current_day}"
            if due(now, t_start) and key not in last_sent:
                kirim(
                    "🟡 🚨 MULAI LOADING\n"
                    "━━━━━━━━━━━━━━━━\n"
                    f"📦 Route : {route}\n"
                    f"🅿️ Slot  : {slot}\n"
                    f"⏰ Jam   : {start_s} WIB\n"
                    "━━━━━━━━━━━━━━━━"
                )
                last_sent.add(key)

            # ==================================================
            # H‑10 FINISH
            # ==================================================
            key = f"H10F|{route}|{slot}|{finish_s}|{current_day}"
            if due(now, h10_finish) and key not in last_sent:
                kirim(
                    "🟠 ⏳ H-10 MENIT SELESAI LOADING\n"
                    "━━━━━━━━━━━━━━━━\n"
                    f"📦 Route : {route}\n"
                    f"🅿️ Slot  : {slot}\n"
                    f"⏰ Jam   : {finish_s} WIB\n"
                    "━━━━━━━━━━━━━━━━"
                )
                last_sent.add(key)

            # ==================================================
            # SELESAI LOADING
            # ==================================================
            key = f"FINISH|{route}|{slot}|{finish_s}|{current_day}"
            if due(now, t_finish) and key not in last_sent:
                kirim(
                    "🟢 ✔ SELESAI LOADING\n"
                    "━━━━━━━━━━━━━━━━\n"
                    f"📦 Route : {route}\n"
                    f"🅿️ Slot  : {slot}\n"
                    f"⏰ Jam   : {finish_s} WIB\n"
                    "━━━━━━━━━━━━━━━━"
                )
                last_sent.add(key)

    # Cek setiap 1 detik (akurasi tinggi)
    time.sleep(1)
