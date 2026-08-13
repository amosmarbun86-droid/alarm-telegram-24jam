import os
import uuid
from groq import Groq
from gtts import gTTS

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

AUDIO_FOLDER = "static/audio"
os.makedirs(AUDIO_FOLDER, exist_ok=True)

latest_announcement = {"id": None, "text": None, "audio_url": None}

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
