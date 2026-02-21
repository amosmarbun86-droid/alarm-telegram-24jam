import pandas as pd
import requests
import time
from datetime import datetime

# =====================
# 🔑 TOKEN TELEGRAM
# =====================
TOKEN = "8526408120:AAHqYHx3n9V3qpAqbp8_UDwfWed5SHC7Wbo"
CHAT_ID = "8559067633"

# =====================
# 📥 LOAD DATA
# =====================
df = pd.read_csv("Jadwal_Route_Siborong_Borong.csv")

# =====================
# 📤 KIRIM TELEGRAM
# =====================
def kirim_telegram(pesan):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": pesan}
    requests.post(url, data=data)

# =====================
# ⏰ CEK JADWAL LOOP
# =====================
print("🔔 BOT AKTIF 24 JAM")

while True:
    sekarang = datetime.now().strftime("%H:%M")

    for i, row in df.iterrows():
        waktu = str(row["Start Loading"])[:5]

        if sekarang == waktu:
            pesan = f"""
🚛 JADWAL ROUTE

Route : {row['Route']}
Slot  : {row['Slot']}
Nopol : {row['Nopol']}

⏰ Start Loading : {waktu}
"""
            kirim_telegram(pesan)
            time.sleep(60)

    time.sleep(10)
