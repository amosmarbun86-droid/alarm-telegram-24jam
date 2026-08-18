import os
import uuid
import wave
import struct
import math
import itertools
import asyncio
import time
import edge_tts
from groq import Groq

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

# Model Groq yang dipakai untuk generate teks pengumuman.
# CATATAN RIWAYAT (biar nggak bolak-balik coba yang sama):
# - "llama-3.3-70b-versatile" -> DIHAPUS/decommission oleh Groq (404).
# - "openai/gpt-oss-120b"     -> reasoning model, dgn max_tokens kecil jawaban
#                                 kepotong jadi teks kosong.
# - "qwen/qwen3.6-27b"        -> jawaban akhir sering nyelip Bahasa Inggris,
#                                 kurang konsisten ikut instruksi Bahasa Indonesia.
# -> Dipakai sekarang: "openai/gpt-oss-20b" (versi lebih kecil, reasoning-nya
#    lebih ringkas jadi lebih nurut instruksi bahasa & max_tokens cukup).
# Kalau suatu saat model ini juga dihapus/error lagi, cek daftar model aktif di:
# https://console.groq.com/settings/limits
GROQ_MODEL = "openai/gpt-oss-20b"

# Suara TTS pakai edge-tts (mesin neural voice Microsoft Edge, gratis tanpa API
# key, hasil jauh lebih natural dibanding gTTS). Voice Indonesia yang dipakai:
# id-ID-ArdiNeural (pria). Kalau mau ganti, tinggal ubah nilai ini, contoh
# alternatif suara wanita: "id-ID-GadisNeural".
TTS_VOICE = "id-ID-ArdiNeural"

AUDIO_FOLDER = "static/audio"
os.makedirs(AUDIO_FOLDER, exist_ok=True)

# Antrian pengumuman: setiap pengumuman baru DITAMBAHKAN ke list ini (bukan
# menimpa satu variabel saja) supaya kalau ada beberapa rute dengan jam yang
# sama persis (mis. 7 jadwal sama-sama START jam 18:20), semua pengumuman
# tetap tersimpan urut dan bisa diputar satu-satu oleh dashboard, tidak ada
# yang ketiban/ke-skip.
_id_counter = itertools.count(1)
announcement_queue = []
MAX_QUEUE = 100  # batas aman, biar list tidak membengkak tanpa henti


def _tambah_ke_queue(text, audio_url):
    item = {"id": next(_id_counter), "text": text, "audio_url": audio_url}
    announcement_queue.append(item)
    # buang entri paling lama kalau sudah kelewat banyak
    if len(announcement_queue) > MAX_QUEUE:
        del announcement_queue[: len(announcement_queue) - MAX_QUEUE]


ALARM_SOUND_PATH = os.path.join(AUDIO_FOLDER, "alarm.wav")
ALARM_SOUND_URL = "/static/audio/alarm.wav"


def _generate_alarm_sound():
    """Bikin file suara alarm (bip nada tinggi, berulang 3x) sekali saat aplikasi
    start. Dipakai sebagai suara pembuka sebelum pengumuman suara (TTS) diputar.
    Di-generate langsung pakai Python (modul wave bawaan), tidak perlu file dari luar."""
    if os.path.exists(ALARM_SOUND_PATH):
        return

    framerate = 22050
    freq = 1500       # Hz - nada tinggi khas alarm
    beep_duration = 0.3
    gap_duration = 0.15
    repeats = 3

    frames = bytearray()
    for _ in range(repeats):
        for i in range(int(framerate * beep_duration)):
            value = int(32767 * 0.6 * math.sin(2 * math.pi * freq * i / framerate))
            frames += struct.pack('<h', value)
        for i in range(int(framerate * gap_duration)):
            frames += struct.pack('<h', 0)

    with wave.open(ALARM_SOUND_PATH, 'w') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(framerate)
        wf.writeframes(bytes(frames))

    print("🔔 Suara alarm berhasil dibuat:", ALARM_SOUND_PATH)


_generate_alarm_sound()

# Deskripsi & catatan per jenis alarm - dipakai untuk menyusun prompt ke Groq.
# "catatan" penting supaya AI tidak salah pakai kata "keberangkatan/berangkat"
# untuk jam MULAI LOADING (yang benar cuma untuk jam SELESAI loading, karena
# mobil baru benar-benar berangkat setelah loading selesai, bukan saat mulai).
JENIS_INFO = {
    "START": {
        "deskripsi": "mobil akan mulai loading barang sekarang",
        "catatan": "Jam yang disebutkan adalah jam MULAI LOADING, BUKAN jam keberangkatan/berangkat. "
                   "Jangan gunakan kata 'keberangkatan' atau 'berangkat' untuk jam ini, cukup sebut 'mulai loading' atau 'proses loading dimulai'.",
    },
    "SELESAI": {
        "deskripsi": "loading barang sudah selesai sekarang dan mobil akan segera berangkat",
        "catatan": "Jam yang disebutkan adalah jam loading SELESAI sekaligus jam mobil akan berangkat, boleh gunakan kata 'berangkat'/'keberangkatan'.",
    },
    "REMINDER": {
        "deskripsi": "pengingat, waktu loading tinggal 10 menit lagi",
        "catatan": "Jam yang disebutkan adalah jam MULAI LOADING, BUKAN jam keberangkatan. "
                   "Jangan gunakan kata 'keberangkatan'/'berangkat', cukup sebut 'mulai loading'.",
    },
    "REMINDER_FREELOAD": {
        "deskripsi": "pengingat, 30 menit lagi mulai loading dan silakan lakukan freeload sebelumnya",
        "catatan": "Jam yang disebutkan adalah jam MULAI LOADING (30 menit lagi), BUKAN jam keberangkatan. "
                   "Jangan gunakan kata 'keberangkatan'/'berangkat', cukup sebut 'mulai loading'.",
    },
    "REMINDER_SELESAI": {
        "deskripsi": "pengingat, loading akan selesai 10 menit lagi",
        "catatan": "Jam yang disebutkan adalah jam loading akan SELESAI (mobil akan segera berangkat setelahnya), boleh gunakan kata 'berangkat'/'keberangkatan'.",
    },
    "SANDAR": {
        "deskripsi": "mobil untuk rute tujuan ini sudah sandar/tiba di lokasi",
        "catatan": "",
    },
}


def _text_to_speech(teks, filepath, voice=TTS_VOICE, percobaan_maks=3):
    """Generate audio dari teks pakai edge-tts (neural voice, natural).
    edge-tts async by design, jadi dijalankan lewat asyncio.run() supaya
    bisa dipanggil biasa dari kode yang sinkron (Flask/loop utama bot.py).

    Otomatis dicoba ulang (retry) kalau gagal, karena kadang server edge-tts
    gagal konek sesaat - terutama kalau ada 2+ pengumuman ke-trigger nyaris
    bersamaan (misalnya beberapa rute dengan jam START yang sama persis)."""
    async def _run():
        communicate = edge_tts.Communicate(teks, voice)
        await communicate.save(filepath)

    error_terakhir = None
    for percobaan in range(1, percobaan_maks + 1):
        try:
            asyncio.run(_run())
            return
        except Exception as e:
            error_terakhir = e
            print(f"⚠️  edge-tts gagal (percobaan {percobaan}/{percobaan_maks}): {repr(e)}")
            if percobaan < percobaan_maks:
                time.sleep(1.5)  # jeda sebentar sebelum coba lagi
    raise error_terakhir


import re

def _bersihkan_reasoning(teks):
    """Sebagian model Groq (termasuk qwen) adalah 'reasoning model' yang
    kadang menyertakan proses berpikirnya dalam blok <think>...</think>
    sebelum jawaban akhir. Buang blok itu, sisakan cuma jawaban aslinya."""
    if not teks:
        return teks
    # buang blok <think>...</think> (bisa multi-baris)
    bersih = re.sub(r"<think>.*?</think>", "", teks, flags=re.DOTALL)
    # jaga-jaga kalau tag penutup </think> ada tapi tag pembuka ketinggalan/lain format
    bersih = re.sub(r"^.*?</think>", "", bersih, flags=re.DOTALL)
    return bersih.strip()


def _teks_fallback(jenis, route, slot, waktu):
    """Teks cadangan dipakai kalau Groq gagal/error, supaya alarm suara TETAP
    bunyi walau AI-nya lagi bermasalah (limit habis, model dihapus, dsb)."""
    slot_text = f" slot {slot}," if slot else ""
    info = JENIS_INFO.get(jenis, {"deskripsi": jenis})
    return f"Perhatian, {info['deskripsi']}. Rute {route},{slot_text} jam {waktu} WIB."


def buat_pengumuman(jenis, route, slot, waktu):
    """Generate teks pengumuman via Groq, lalu convert ke audio (edge-tts).
    Tambahkan hasilnya ke antrian (announcement_queue) supaya dashboard bisa polling & auto-play.

    Kalau Groq error/limit/model dihapus, tetap lanjut pakai teks fallback
    supaya alarm suara TIDAK BISU/tidak diam, dan errornya dicetak jelas ke log."""
    teks = None

    if not groq_client:
        print("⚠️  GROQ_API_KEY belum diset, pakai teks fallback (tanpa AI).")
        teks = _teks_fallback(jenis, route, slot, waktu)
    else:
        try:
            slot_text = f" slot {slot}," if slot else ""
            info = JENIS_INFO.get(jenis, {"deskripsi": jenis, "catatan": ""})
            deskripsi = info["deskripsi"]
            catatan = info["catatan"]
            catatan_text = f" {catatan}" if catatan else ""
            prompt = (
                f"WAJIB Bahasa Indonesia, DILARANG Bahasa Inggris. "
                f"Buatkan satu kalimat pengumuman singkat dan formal untuk sistem alarm "
                f"logistik pengiriman barang menggunakan mobil/truk. Situasi: {deskripsi}. "
                f"Rute: {route},{slot_text} jam {waktu} WIB.{catatan_text} "
                f"Bahasa Indonesia, tanpa tanda kutip, langsung kalimatnya saja."
            )

            response = groq_client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Kamu adalah asisten yang HANYA boleh menjawab dalam "
                            "Bahasa Indonesia. Dilarang keras menggunakan Bahasa "
                            "Inggris atau bahasa lain sama sekali dalam jawaban akhir. "
                            "Jawab langsung satu kalimat saja, tanpa penjelasan, "
                            "tanpa proses berpikir, tanpa tanda kutip."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=200
            )
            teks_mentah = (response.choices[0].message.content or "").strip()
            teks = _bersihkan_reasoning(teks_mentah)

            # Kalau ternyata masih kosong (model berubah lagi / balikin format
            # aneh), langsung pakai fallback daripada bikin file audio bisu.
            if not teks:
                print(f"⚠️  Groq balikin teks kosong (model={GROQ_MODEL}), pakai fallback.")
                teks = _teks_fallback(jenis, route, slot, waktu)

        except Exception as e:
            # Cetak jelas: jenis error + model yang dipakai, biar gampang didiagnosa
            # dari log (misalnya kalau modelnya suatu saat dihapus lagi oleh Groq).
            print(f"❌ GROQ ERROR (model={GROQ_MODEL}):", repr(e))
            teks = _teks_fallback(jenis, route, slot, waktu)

    try:
        audio_id = str(uuid.uuid4())
        filename = f"{audio_id}.mp3"
        filepath = os.path.join(AUDIO_FOLDER, filename)

        _text_to_speech(teks, filepath)

        audio_url = f"/static/audio/{filename}"
        _tambah_ke_queue(teks, audio_url)

        print(f"🔊 Pengumuman dibuat: {teks}")

    except Exception as e:
        print(f"❌ TTS/QUEUE ERROR [{jenis} | {route} | slot {slot} | jam {waktu}]: {repr(e)}")
        print(f"   -> Pengumuman untuk kejadian ini GAGAL dibuat setelah beberapa kali percobaan.")
