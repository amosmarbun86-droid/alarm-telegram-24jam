import os
import uuid
import wave
import struct
import math
import itertools
import asyncio
import edge_tts
from groq import Groq

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

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

# Deskripsi situasi per jenis alarm - dipakai untuk menyusun prompt ke Groq
JENIS_DESKRIPSI = {
    "START": "mobil akan mulai loading barang sekarang",
    "SELESAI": "loading barang sudah selesai sekarang dan mobil akan segera berangkat",
    "REMINDER": "pengingat, waktu loading tinggal 10 menit lagi",
    "REMINDER_FREELOAD": "pengingat, 30 menit lagi mulai loading dan silakan lakukan freeload sebelumnya",
    "REMINDER_SELESAI": "pengingat, loading akan selesai 10 menit lagi",
    "SANDAR": "mobil untuk rute tujuan ini sudah sandar/tiba di lokasi",
}


def _text_to_speech(teks, filepath, voice=TTS_VOICE):
    """Generate audio dari teks pakai edge-tts (neural voice, natural).
    edge-tts async by design, jadi dijalankan lewat asyncio.run() supaya
    bisa dipanggil biasa dari kode yang sinkron (Flask/loop utama bot.py)."""
    async def _run():
        communicate = edge_tts.Communicate(teks, voice)
        await communicate.save(filepath)
    asyncio.run(_run())


def buat_pengumuman(jenis, route, slot, waktu):
    """Generate teks pengumuman via Groq, lalu convert ke audio (edge-tts).
    Tambahkan hasilnya ke antrian (announcement_queue) supaya dashboard bisa polling & auto-play."""
    if not groq_client:
        print("⚠️  GROQ_API_KEY belum diset, pengumuman suara dilewati.")
        return

    try:
        slot_text = f" slot {slot}," if slot else ""
        deskripsi = JENIS_DESKRIPSI.get(jenis, jenis)
        prompt = (
            f"Buatkan satu kalimat pengumuman singkat dan formal untuk sistem alarm "
            f"logistik pengiriman barang menggunakan mobil/truk. Situasi: {deskripsi}. "
            f"Rute: {route},{slot_text} jam {waktu} WIB. Bahasa Indonesia, tanpa tanda kutip, langsung kalimatnya saja."
        )

        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=100
        )
        teks = response.choices[0].message.content.strip()

        audio_id = str(uuid.uuid4())
        filename = f"{audio_id}.mp3"
        filepath = os.path.join(AUDIO_FOLDER, filename)

        _text_to_speech(teks, filepath)

        audio_url = f"/static/audio/{filename}"
        _tambah_ke_queue(teks, audio_url)

        print(f"🔊 Pengumuman dibuat: {teks}")

    except Exception as e:
        print("PENGUMUMAN ERROR:", e)
