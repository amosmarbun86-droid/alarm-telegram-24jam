import pandas as pd
import time
import requests
from datetime import datetime, timedelta

TOKEN = "8526408120:AAHqYHx3n9V3qpAqbp8_UDwfWed5SHC7Wbo"
CHAT_ID = "8559067633"
CSV_FILE = "jadwal.csv"

def kirim(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": msg}
    requests.post(url, data=data)

print("BOT AKTIF 24 JAM")

while True:
    try:
        df = pd.read_csv(CSV_FILE)
        df.columns = df.columns.str.strip().str.lower()

        now = datetime.now()

        for _, row in df.iterrows():

            route = str(row.get("route", ""))
            start_loading = str(row.get("start loading", ""))
            selesai_loading = str(row.get("selesai loading", ""))

            if start_loading and start_loading != "nan":
                t = datetime.strptime(start_loading, "%H:%M")
                t = now.replace(hour=t.hour, minute=t.minute)

                if abs((now - t).total_seconds()) < 30:
                    kirim(f"START LOADING {route} {start_loading}")

                reminder = t - timedelta(minutes=10)
                if abs((now - reminder).total_seconds()) < 30:
                    kirim(f"H-10 START LOADING {route} {start_loading}")

            if selesai_loading and selesai_loading != "nan":
                t = datetime.strptime(selesai_loading, "%H:%M")
                t = now.replace(hour=t.hour, minute=t.minute)

                if abs((now - t).total_seconds()) < 30:
                    kirim(f"SELESAI LOADING {route} {selesai_loading}")

                reminder = t - timedelta(minutes=10)
                if abs((now - reminder).total_seconds()) < 30:
                    kirim(f"H-10 SELESAI {route} {selesai_loading}")

        time.sleep(30)

    except Exception as e:
        print("ERROR:", e)
        time.sleep(10)
