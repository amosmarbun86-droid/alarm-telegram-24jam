# Alarm Dashboard 24 Jam

Sistem alarm & dashboard jadwal loading/keberangkatan mobil logistik, berjalan 24 jam. Dibangun dengan Python (Flask) + Firebase Realtime Database, dengan notifikasi Telegram dan pengumuman suara otomatis (Groq AI + Text-to-Speech).

## Fitur Utama

**Dashboard Web**
- Tabel jadwal route dengan warna otomatis per rute
- Status baris otomatis berdasarkan waktu real-time:
  - 🔵 **Proses Freeload** — H-30 menit sebelum jam START
  - 🟡 **Sedang Proses** — dari jam START sampai jam SELESAI
  - ✅ **Selesai** — setelah jam SELESAI
- Auto-refresh tabel tiap 30 detik (tanpa perlu refresh manual)
- **Filter/pencarian tabel** — cari berdasarkan nama rute, dan/atau filter berdasarkan status (Proses Freeload / Sedang Proses / Selesai / Belum Mulai)
- **Mode Gelap** — toggle dark mode, preferensi tersimpan otomatis per device
- Tambah / Edit / Hapus jadwal (dilindungi password)
- Toggle manual "Sudah Sandar" per rute, otomatis reset tiap hari
- Link Google Maps otomatis untuk rute yang formatnya `Asal > Hub1 - Hub2 - Hub3`
- PWA (bisa di-install ke homescreen, punya ikon & manifest sendiri)

**Notifikasi Telegram**
- Alarm otomatis saat waktu START loading & SELESAI loading
- Reminder H-10 menit sebelum START
- Reminder H-15 menit sebelum SELESAI
- Command bot: `/start` (menu), `status`, `test`, `jadwal`, `reload`
- Reminder H-30 menit (freeload) **sengaja tidak dikirim ke Telegram** — cuma suara di dashboard, karena Telegram tidak dipakai untuk komunikasi kerja sehari-hari

**Pengumuman Suara Otomatis (Groq + edge-tts)**
- Teks pengumuman dibuat otomatis oleh Groq AI (model `openai/gpt-oss-20b`) sesuai konteks (START, SELESAI, reminder, freeload, atau status Sandar)
- Prompt ke AI sudah diberi instruksi tegas soal istilah waktu, supaya tidak salah sebut "keberangkatan" untuk jam mulai loading (kata "keberangkatan"/"berangkat" cuma dipakai untuk jam SELESAI, karena mobil baru benar-benar berangkat setelah loading kelar)
- Prompt & system message mewajibkan output Bahasa Indonesia (mencegah model kadang jawab pakai Bahasa Inggris), dan reasoning-token (`<think>...</think>`) dari model otomatis dibersihkan sebelum jadi suara
- **Fallback otomatis** — kalau Groq error/limit habis/model di-decommission, sistem tetap pakai teks cadangan sederhana supaya alarm suara tetap bunyi (tidak bisu), errornya dicetak jelas ke log Render buat didiagnosa
- Diubah jadi suara Bahasa Indonesia via **edge-tts** (neural voice Microsoft Edge, gratis tanpa API key, jauh lebih natural dibanding gTTS) — voice default: `id-ID-ArdiNeural` (pria)
- Suara alarm (bip nada tinggi) diputar dulu sebelum pengumuman suara menyusul
- **Sistem antrian suara** — semua pengumuman ditampung di antrian (bukan cuma yang terakhir), lalu diputar satu-satu berurutan. Ini penting kalau ada beberapa rute dengan jam START/SELESAI yang sama persis (misalnya 7 jadwal bareng), supaya tidak ada pengumuman yang ke-skip
- Dashboard polling tiap 5 detik untuk mendeteksi pengumuman baru dan memutar suara otomatis di device yang membuka dashboard (harus klik "Aktifkan Suara" sekali per sesi/device)
- Trigger otomatis juga saat operator menandai "Sudah Sandar" secara manual di dashboard

> ⚠️ Groq beberapa kali men-decommission model tanpa pemberitahuan panjang (pernah terjadi pada `llama-3.3-70b-versatile`). Kalau pengumuman suara tiba-tiba berhenti/error terus di log Render dengan pesan `GROQ ERROR`, cek daftar model aktif di [console.groq.com/settings/limits](https://console.groq.com/settings/limits) dan update nilai `GROQ_MODEL` di `announcer.py`.

## Struktur Project

```
alarm-dashboard-24jam/
├── bot.py              # Entry point utama: Flask dashboard + alarm loop + command Telegram
├── announcer.py         # Modul Groq (generate teks) + edge-tts (convert ke suara) + alarm bip + antrian suara
├── requirements.txt      # Dependencies Python
├── Procfile              # Start command untuk Render (web: python bot.py)
├── jadwal.csv            # Data lama, hanya dipakai untuk migrasi sekali ke Firebase
└── static/audio/         # File suara sementara (alarm.wav + hasil TTS), dibuat otomatis saat runtime
```

> Catatan: `dashboard.py` dan `templates/index.html` dari versi lama sudah tidak dipakai (dashboard aktif sekarang di-render langsung dari `bot.py`) — boleh dihapus dari repo kalau belum.

## Environment Variables (diset di Render)

| Variable | Keterangan |
|---|---|
| `BOT_TOKEN` | Token Bot Telegram |
| `CHAT_ID` | Chat ID tujuan notifikasi Telegram |
| `DASHBOARD_PASSWORD` | Password untuk aksi tambah/edit/hapus/toggle di dashboard |
| `FIREBASE_DB_URL` | URL Firebase Realtime Database |
| `GROQ_API_KEY` | API key Groq, dipakai untuk generate teks pengumuman suara |

> edge-tts tidak butuh API key tambahan — gratis dan langsung jalan begitu library `edge-tts` terpasang dari `requirements.txt`.

## Deployment

Dideploy di [Render](https://render.com) (Free tier), dengan [UptimeRobot](https://uptimerobot.com) untuk mencegah server spin-down karena inaktivitas.

**Start Command:** `python bot.py`

## Cara Kerja Alarm

Loop utama (`while True` di `bot.py`) mengecek tiap detik:
1. **Command Telegram** — cek pesan baru dari user
2. **Jadwal alarm** — bandingkan waktu sekarang dengan jam START/SELESAI tiap rute (toleransi ±30 detik):
   - H-30 menit sebelum START → reminder freeload, **suara saja** (tanpa Telegram)
   - H-10 menit sebelum START → reminder + notifikasi Telegram + suara
   - START loading → notifikasi Telegram + suara
   - H-15 menit sebelum SELESAI → reminder + notifikasi Telegram + suara
   - SELESAI loading → notifikasi Telegram + suara

Kalau ada beberapa rute dengan jam yang sama persis, semua pengumuman suaranya tetap tersimpan di antrian dan diputar berurutan (lihat bagian "Pengumuman Suara Otomatis" di atas), tidak ada yang ke-skip.

Data jadwal diambil real-time dari Firebase Realtime Database via REST API (`fb_get`, `fb_post`, `fb_put`, `fb_patch`, `fb_delete`).
