import time
import uuid
import pandas as pd
import numpy as np
from pylsl import resolve_streams, StreamInlet  # <--- Perbaikan Import di sini
import os

# --- KONFIGURASI ---
SUBJEK_NAMA = "Subjek_01"  # Ganti nama subjek setiap ganti orang
DURASI_IMAJINASI = 4      # Berapa detik subjek membayangkan kata
JUMLAH_TRIAL = 5          # Berapa kali pengulangan per kata
KATA_TARGET = [           # 10 Kata Target Skripsi Anda
    "Makan", "Minum", "Berak", "Pipis", "Mandi", 
    "Bosan", "Lelah", "Sakit", "Sayang", "Tidur"
]

def find_target_stream(target_type='BandPower'):
    """Fungsi helper untuk mencari stream secara manual"""
    print(f"[-] Mencari Stream LSL tipe '{target_type}'...")
    while True:
        # Ambil semua stream yang aktif di jaringan
        streams = resolve_streams() 
        
        for stream in streams:
            if stream.type() == target_type:
                print(f"[+] Ditemukan Stream: {stream.name()} (ID: {stream.source_id()})")
                return stream
        
        # Jika belum ketemu, tunggu sebentar lalu cari lagi
        print(".", end='', flush=True)
        time.sleep(1.0)

def record_data():
    # 1. Cari Stream
    target_stream = find_target_stream('BandPower')
    
    if not target_stream:
        print("[X] Stream gagal ditemukan.")
        return

    # 2. Buat Inlet
    inlet = StreamInlet(target_stream)
    print(f"[+] Terhubung ke stream: {inlet.info().name()}")
    
    # Ambil nama channel dari metadata stream
    info = inlet.info()
    ch = info.desc().child("channels").child("channel")
    col_names = ["Timestamp", "Label"]
    
    # Loop untuk mengambil semua nama channel
    for k in range(info.channel_count()):
        label = ch.child_value("label")
        # Jika label kosong (kadang terjadi), beri nama default
        if not label:
            label = f"Ch_{k+1}"
        col_names.append(label)
        ch = ch.next_sibling()
        
    all_data = []
    
    print("\n" + "="*40)
    print(f"   MULAI PEREKAMAN: {SUBJEK_NAMA}")
    print(f"   Total Kata: {len(KATA_TARGET)}")
    print(f"   Pengulangan: {JUMLAH_TRIAL}x")
    print("="*40 + "\n")
    
    input(">>> Tekan ENTER untuk memulai sesi...")

    for trial in range(1, JUMLAH_TRIAL + 1):
        print(f"\n--- PENGULANGAN KE-{trial} DARI {JUMLAH_TRIAL} ---")
        
        for kata in KATA_TARGET:
            # 1. Instruksi Rileks
            print(f"\n[Persiapan] Rileks sejenak... (Tarik napas)")
            time.sleep(2) 
            
            # 2. Tampilkan Stimulus
            print(f"\n>>> FOKUS! Bayangkan kata:  [ {kata.upper()} ]  <<<")
            
            # 3. Rekam Data
            start_time = time.time()
            # Kosongkan buffer lama agar data bersih
            try:
                inlet.flush() 
            except: 
                pass # Abaikan jika flush gagal di beberapa versi
            
            while (time.time() - start_time) < DURASI_IMAJINASI:
                # Tarik sampel dengan timeout singkat
                sample, timestamp = inlet.pull_sample(timeout=0.1)
                if sample:
                    # Simpan: [Waktu, LabelKata, Data1, Data2, ...]
                    row = [timestamp, kata] + sample
                    all_data.append(row)
            
            print("   (Selesai)")
            
    # --- SIMPAN DATA KE CSV ---
    print("\n[+] Menyimpan Data...")
    
    # Path folder: backend/../../dataset/Subjek_01
    base_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.join(base_dir, "..", "..", "..") # Mundur ke root
    save_dir = os.path.join(project_root, "dataset", SUBJEK_NAMA)
    
    os.makedirs(save_dir, exist_ok=True)
    
    filename = f"{SUBJEK_NAMA}_recording_{uuid.uuid4().hex[:8]}.csv"
    filepath = os.path.join(save_dir, filename)
    
    try:
        df = pd.DataFrame(all_data, columns=col_names)
        df.to_csv(filepath, index=False)
        print(f"[SUCCESS] Data tersimpan di: {filepath}")
        print(f"Total Sampel: {len(df)}")
        print(f"Preview Data:\n{df.head(2)}")
    except Exception as e:
        print(f"[ERROR] Gagal menyimpan CSV: {e}")
        # Backup simpan manual jika pandas error
        print("Mencoba simpan raw backup...")
        with open(filepath + ".txt", "w") as f:
            for line in all_data:
                f.write(str(line) + "\n")

if __name__ == "__main__":
    try:
        record_data()
    except KeyboardInterrupt:
        print("\n[!] Perekaman dihentikan pengguna.")