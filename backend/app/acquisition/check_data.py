import pandas as pd
import matplotlib.pyplot as plt
import glob
import os

def visualize_latest_csv():
    # 1. SETUP PATH YANG LEBIH KUAT (Absolute Path)
    # Ambil lokasi file script ini berada (backend/app/acquisition)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Mundur 3 folder ke belakang untuk ke root: acquisition -> app -> backend -> ROOT
    project_root = os.path.abspath(os.path.join(script_dir, "..", "..", ".."))
    # Masuk ke folder dataset
    dataset_dir = os.path.join(project_root, "dataset")
    
    print(f"[*] Mencari data di folder: {dataset_dir}")

    # 2. Cari file CSV (Recursive search di dalam semua folder subjek)
    search_pattern = os.path.join(dataset_dir, "**", "*.csv")
    files = glob.glob(search_pattern, recursive=True)
    
    if not files:
        print("\n[X] Belum ada file CSV ditemukan.")
        print("    Coba cek apakah folder 'dataset' ada isinya?")
        return

    # Ambil file yang paling baru dibuat (Latest)
    latest_file = max(files, key=os.path.getctime)
    print(f"[+] Menganalisis file terbaru: {os.path.basename(latest_file)}")
    
    try:
        df = pd.read_csv(latest_file)
    except Exception as e:
        print(f"[X] Gagal membaca CSV: {e}")
        return
    
    # 3. Filter data berdasarkan label (Misal: 'Makan')
    # Kita cari label apa saja yang ada di file
    unique_labels = df['Label'].unique()
    target_label = unique_labels[0] # Ambil label pertama yang ketemu
    
    print(f"[*] Menampilkan grafik untuk kata: '{target_label}'")
    
    df_filtered = df[df['Label'] == target_label]
    
    if df_filtered.empty:
        print(f"Data kosong untuk label {target_label}")
        return

    # 4. Plot Grafik Gelombang
    plt.figure(figsize=(12, 6))
    
    # Plot Sensor AF3 (Frontal Kiri)
    # Cek nama kolom yang tersedia (karena kadang nama kolom beda dikit)
    cols = df.columns
    
    # Helper untuk cari kolom
    def get_col(sensor, band):
        matches = [c for c in cols if sensor in c and band in c]
        return matches[0] if matches else None

    # Kita coba plot Alpha dan Beta untuk sensor AF3
    col_alpha = get_col("AF3", "Alpha")
    col_beta = get_col("AF3", "HighBeta") # atau LowBeta
    
    if col_alpha and col_beta:
        plt.plot(df_filtered['Timestamp'], df_filtered[col_alpha], label='AF3 Alpha (Rileks)', color='green', linewidth=2)
        plt.plot(df_filtered['Timestamp'], df_filtered[col_beta], label='AF3 Beta (Fokus)', color='red', linewidth=2)
    else:
        # Fallback jika nama kolom tidak ketemu, plot kolom ke-3 dan ke-4
        print("[!] Nama kolom spesifik tidak ketemu, plot kolom index 2 dan 3...")
        plt.plot(df_filtered.iloc[:, 0], df_filtered.iloc[:, 2], label=df.columns[2])
        plt.plot(df_filtered.iloc[:, 0], df_filtered.iloc[:, 3], label=df.columns[3])
    
    plt.title(f"Visualisasi Sinyal Otak: '{target_label}' (File: {os.path.basename(latest_file)})")
    plt.xlabel("Waktu (Timestamp)")
    plt.ylabel("Power Spectral Density (uV^2/Hz)")
    plt.legend()
    plt.grid(True, linestyle='--', alpha=0.7)
    
    print("[*] Menampilkan grafik... (Cek window baru yang muncul)")
    plt.show()

if __name__ == "__main__":
    visualize_latest_csv()