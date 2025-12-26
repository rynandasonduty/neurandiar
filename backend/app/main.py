# backend/app/main.py
from fastapi import FastAPI

app = FastAPI(title="BCI Speller API", version="1.0.0")

@app.get("/")
def read_root():
    return {"status": "active", "message": "Sistem BCI Siap - Silakan nyalakan Driver Emotiv"}

@app.get("/health")
def health_check():
    # Nanti di sini kita cek apakah LSL stream terdeteksi
    return {"lsl_stream_connected": False}