import asyncio
import json
import ssl
import time
import os
import signal
import sys
from websocket import create_connection
from pylsl import StreamInfo, StreamOutlet
from dotenv import load_dotenv

# Load credentials
load_dotenv()
CLIENT_ID = os.getenv("EMOTIV_CLIENT_ID")
CLIENT_SECRET = os.getenv("EMOTIV_CLIENT_SECRET")

class CortexLSLBridge:
    def __init__(self):
        self.ws = None
        self.url = "wss://localhost:6868"
        self.auth_token = None
        self.session_id = None
        self.headset_id = None
        self.streams = ['pow'] 
        self.lsl_outlet = None
        self.is_running = True
        
        if not CLIENT_ID or not CLIENT_SECRET:
            raise ValueError("Harap isi EMOTIV_CLIENT_ID dan EMOTIV_CLIENT_SECRET di file .env")

    def connect(self):
        print(f"[*] Menghubungkan ke Emotiv Launcher ({self.url})...")
        self.ws = create_connection(self.url, sslopt={"cert_reqs": ssl.CERT_NONE})
        print("[+] Terhubung ke WebSocket Emotiv.")

    def send_request(self, method, params=None, req_id=1):
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {},
            "id": req_id
        }
        if self.ws:
            self.ws.send(json.dumps(payload))
            result = self.ws.recv()
            return json.loads(result)
        return None

    def request_access(self):
        print("[*] Langkah 1: Meminta Akses (Request Access)...")
        res = self.send_request("requestAccess", {
            "clientId": CLIENT_ID,
            "clientSecret": CLIENT_SECRET
        })
        if res and 'result' in res and 'accessGranted' in res['result']:
            if not res['result']['accessGranted']:
                print("\n[!] TOLONG CEK LAUNCHER DAN KLIK APPROVE!\n")
                time.sleep(5)

    def authorize(self, debit_amount=0):
        """
        Mencoba authorize dengan jumlah debit tertentu.
        """
        print(f"[*] Langkah 2: Otorisasi (Authorize) dengan debit={debit_amount}...")
        res = self.send_request("authorize", {
            "clientId": CLIENT_ID,
            "clientSecret": CLIENT_SECRET,
            "debit": debit_amount
        })
        
        if res and 'result' in res and 'cortexToken' in res['result']:
            self.auth_token = res['result']['cortexToken']
            print("[+] Otorisasi Berhasil!")
            return True
        elif res and 'error' in res:
            print(f"[-] Authorize Gagal (debit={debit_amount}): {res['error']['message']}")
            return False
        return False

    def get_license_info(self):
        """
        Fungsi DIAGNOSIS: Melihat isi kuota akun.
        """
        print("[*] Mengambil Info Lisensi (getLicenseInfo)...")
        res = self.send_request("getLicenseInfo", {"cortexToken": self.auth_token})
        
        if res and 'result' in res:
            info = res['result']
            print("\n" + "="*40)
            print("         STATUS LISENSI AKUN")
            print("="*40)
            print(f" - License ID  : {info.get('licenseId', 'N/A')}")
            print(f" - Local Quota : {info.get('localQuota', 0)} (Sisa sesi di PC ini)")
            print(f" - Total Quota : {info.get('sessionCount', 0)} (Total jatah)")
            print(f" - Hard Limit  : {info.get('hardLimit', 'N/A')}")
            print(f" - Expired     : {info.get('expired', 'N/A')}")
            print("="*40 + "\n")
            return info
        else:
            print("[-] Gagal mengambil License Info.")
            return None

    def query_headset(self):
        print("[*] Mencari Headset...")
        res = self.send_request("queryHeadsets")
        if res and 'result' in res:
            for headset in res['result']:
                if headset['status'] in ['connected', 'discovered']:
                    self.headset_id = headset['id']
                    print(f"[+] Headset: {self.headset_id} ({headset['status']})")
                    return True
        print("[-] Menunggu Headset Connected...")
        return False

    def create_session(self):
        # Cek Zombie Session dulu (Penting!)
        print("[*] Cek sesi aktif...")
        sessions = self.send_request("querySessions", {"cortexToken": self.auth_token})
        if sessions and 'result' in sessions and len(sessions['result']) > 0:
            self.session_id = sessions['result'][0]['id']
            print(f"[!] Menemukan Sesi Lama: {self.session_id}. Menggunakannya kembali.")
            # Coba aktifkan sesi lama
            self.send_request("updateSession", {"cortexToken": self.auth_token, "session": self.session_id, "status": "active"})
            return

        print("[*] Membuat Sesi BARU...")
        res = self.send_request("createSession", {
            "cortexToken": self.auth_token,
            "headset": self.headset_id,
            "status": "active"
        })
        
        if res and 'result' in res:
            self.session_id = res['result']['id']
            print(f"[+] Sesi Baru Berhasil Dibuat: {self.session_id}")
        else:
            # Jika gagal, kita print error lengkapnya
            error_msg = res['error']['message'] if 'error' in res else str(res)
            raise Exception(f"Gagal Create Session: {error_msg}")

    def close_session(self):
        if self.session_id and self.auth_token:
            print(f"\n[*] Menutup Sesi {self.session_id}...")
            self.send_request("updateSession", {
                "cortexToken": self.auth_token,
                "session": self.session_id,
                "status": "close"
            })
            print("[+] Sesi Ditutup.")

    def setup_lsl(self):
        print("[*] Setup LSL Outlet (Band Power)...")
        info = StreamInfo("EmotivBandPower", "BandPower", 70, 8, 'float32', self.headset_id)
        chns = info.desc().append_child("channels")
        sensors = ["AF3", "F7", "F3", "FC5", "T7", "P7", "O1", "O2", "P8", "T8", "FC6", "F4", "F8", "AF4"]
        bands = ["Theta", "Alpha", "LowBeta", "HighBeta", "Gamma"]
        for s in sensors:
            for b in bands:
                chns.append_child("channel").append_child_value("label", f"{s}_{b}")
        self.lsl_outlet = StreamOutlet(info)
        print("[+] LSL Outlet Siap.")

    def start_stream(self):
        print(f"[*] Subscribe ke {self.streams}...")
        res = self.send_request("subscribe", {
            "cortexToken": self.auth_token,
            "session": self.session_id,
            "streams": self.streams
        })
        if not res or 'result' not in res:
             print(f"[-] Gagal Subscribe: {res}")
             return

        self.setup_lsl()
        print("\n=== STREAMING AKTIF (POW) ===")
        print("Ctrl+C untuk Stop.\n")
        
        while self.is_running:
            try:
                res = self.ws.recv()
                data = json.loads(res)
                if 'pow' in data:
                    sample = data['pow']
                    if sample:
                        self.lsl_outlet.push_sample(sample)
                        print(f"POW: {sample[0]:.2f}, {sample[1]:.2f}...", end='\r')
            except Exception as e:
                pass

    def run(self):
        try:
            self.connect()
            self.request_access()
            
            # --- LOGIKA BARU: COBA DEBIT 1 DULU ---
            # Sesuai saran Emotiv: "Call authorize with a debit of 1... to increase local quota"
            if not self.authorize(debit_amount=1):
                print("[!] Gagal debit=1, mencoba fallback ke debit=0...")
                if not self.authorize(debit_amount=0):
                    raise Exception("Gagal Login sepenuhnya.")
            
            # --- DIAGNOSIS KUOTA ---
            self.get_license_info()
            
            while not self.query_headset(): time.sleep(5)
            self.create_session()
            self.start_stream()
        except KeyboardInterrupt:
            print("\n[!] User Stopping...")
        except Exception as e:
            print(f"\n[ERROR FATAL] {e}")
        finally:
            self.close_session()
            if self.ws: self.ws.close()

if __name__ == "__main__":
    bridge = CortexLSLBridge()
    bridge.run()