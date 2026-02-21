import streamlit as st
import pandas as pd

st.title("🚛 Dashboard Monitoring Jadwal")

df = pd.read_csv("Jadwal_Route_Siborong_Borong.csv")

# Hapus kolom Nopol jika ada
if "Nopol" in df.columns:
    df = df.drop(columns=["Nopol"])

st.subheader("📋 Data Jadwal")
st.dataframe(df)

st.success("Bot Telegram berjalan 24 jam di server")
