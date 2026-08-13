# alarm-telegram-24jam

Sistem alarm & dashboard jadwal loading/keberangkatan mobil logistik, berjalan 24 jam. Dibangun dengan Python (Flask) + Firebase Realtime Database, dengan notifikasi Telegram dan pengumuman suara otomatis (Groq AI + Text-to-Speech).

## Fitur Utama

**Dashboard Web**
- Tabel jadwal route dengan warna otomatis per rute
- Status baris otomatis: 🟡 Sedang Proses / ✅ Selesai (berdasarkan waktu real-time)
- Auto-refresh tabel tiap 30 detik (tanpa perlu refresh manual)
- Tambah / Edit / Hapus jadwal (dilindungi password)
- Toggle manual "Sudah Sandar" per rute, otomatis reset tiap hari
- Link Google Maps otomatis untuk rute yang formatnya `Asal > Hub1 - Hub2 - Hub3`
- PWA (bisa di-install ke homescreen, punya ikon & manifest sendiri)

**Notifikasi Telegram**
- Alarm otomatis saat waktu START loading & SELESAI loading
- Reminder H-10 menit sebelum START
- Reminder H-15 menit sebelum SELESAI
- Command bot: `/start` (menu), `status`, `test`, `jadwal`, `reload`

**Pengumuman Suara Otomatis (Groq + gTTS)**
- Teks pengumuman dibuat otomatis oleh Groq AI (model `llama-3.3-70b-versatile`) sesuai konteks (START, SELESAI, reminder, atau status Sandar)
- Diubah jadi suara Bahasa Indonesia (gTTS)
- Suara alarm (bip nada tinggi) diputar dulu sebelum pengumuman suara menyusul
- Dashboard polling tiap 5 detik untuk mendeteksi pengumuman baru dan memutar suara otomatis di device yang membuka dashboard (harus klik "Aktifkan Suara" sekali per sesi)
- Trigger otomatis juga saat operator menandai "Sudah Sandar" secara manual di dashboard

## Struktur Project

```
alarm-telegram-24jam/
├── bot.py              # Entry point utama: Flask dashboard + alarm loop + command Telegram
├── announcer.py         # Modul Groq (generate teks) + gTTS (convert ke suara) + alarm bip
├── requirements.txt      # Dependencies Python
├── Procfile              # Start command untuk Render (web: python bot.py)
├── jadwal.csv            # Data lama, hanya dipakai untuk migrasi sekali ke Firebase
└── static/audio/         # File suara sementara (alarm.wav + hasil TTS), dibuat otomatis saat runtime
```

## Environment Variables (diset di Render)

| Variable | Keterangan |
|---|---|
| `BOT_TOKEN` | Token Bot Telegram |
| `CHAT_ID` | Chat ID tujuan notifikasi Telegram |
| `DASHBOARD_PASSWORD` | Password untuk aksi tambah/edit/hapus/toggle di dashboard |
| `FIREBASE_DB_URL` | URL Firebase Realtime Database |
| `GROQ_API_KEY` | API key Groq, dipakai untuk generate teks pengumuman suara |

## Deployment

Dideploy di [Render](https://render.com) (Free tier), dengan [UptimeRobot](https://uptimerobot.com) untuk mencegah server spin-down karena inaktivitas.

**Start Command:** `python bot.py`

## Cara Kerja Alarm

Loop utama (`while True` di `bot.py`) mengecek tiap detik:
1. **Command Telegram** — cek pesan baru dari user
2. **Jadwal alarm** — bandingkan waktu sekarang dengan jam START/SELESAI tiap rute (toleransi ±30 detik):
   - START loading → notifikasi + suara
   - H-10 menit sebelum START → reminder + suara
   - SELESAI loading → notifikasi + suara
   - H-15 menit sebelum SELESAI → reminder + suara

Data jadwal diambil real-time dari Firebase Realtime Database via REST API (`fb_get`, `fb_post`, `fb_put`, `fb_patch`, `fb_delete`).
