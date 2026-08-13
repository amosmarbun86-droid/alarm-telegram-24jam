import os
import uuid
import wave
import struct
import math
from groq import Groq
from gtts import gTTS

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

AUDIO_FOLDER = "static/audio"
os.makedirs(AUDIO_FOLDER, exist_ok=True)

latest_announcement = {"id": None, "text": None, "audio_url": None}

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
    "SELESAI": "loading barang sudah selesai sekarang",
    "REMINDER": "pengingat, waktu loading tinggal 10 menit lagi",
    "REMINDER_SELESAI": "pengingat, loading akan selesai dalam 15 menit lagi",
    "SANDAR": "mobil untuk rute tujuan ini sudah sandar/tiba di lokasi",
}


def buat_pengumuman(jenis, route, slot, waktu):
    """Generate teks pengumuman via Groq, lalu convert ke audio (gTTS).
    Update dict latest_announcement supaya dashboard bisa polling & auto-play."""
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

        tts = gTTS(text=teks, lang='id')
        tts.save(filepath)

        latest_announcement["id"] = audio_id
        latest_announcement["text"] = teks
        latest_announcement["audio_url"] = f"/static/audio/{filename}"

        print(f"🔊 Pengumuman dibuat: {teks}")

    except Exception as e:
        print("PENGUMUMAN ERROR:", e)
