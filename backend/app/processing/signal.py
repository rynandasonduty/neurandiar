# backend/app/processing/signal.py
import numpy as np
from scipy.signal import butter, lfilter

class SignalProcessor:
    def __init__(self, sample_rate=256):
        self.fs = sample_rate
        # Inisialisasi Filter (Butterworth Bandpass 0.5 - 50 Hz)
        self.b, self.a = butter(4, [0.5, 50], btype='band', fs=self.fs)

    def apply_filter(self, data_chunk):
        """
        Menerapkan filter ke data mentah.
        data_chunk: numpy array (channels x samples)
        """
        # Note: Untuk real-time streaming, lebih baik pakai lfilter_zi (stateful)
        # Tapi untuk baseline awal, lfilter biasa cukup.
        filtered_data = lfilter(self.b, self.a, data_chunk, axis=1)
        return filtered_data

    def create_epoch(self, continuous_data, marker_index, t_min=-0.2, t_max=0.8):
        """
        Memotong data menjadi window (Epoching) berdasarkan marker.
        """
        start_sample = int(marker_index + t_min * self.fs)
        end_sample = int(marker_index + t_max * self.fs)
        return continuous_data[:, start_sample:end_sample]

# Cara pakai nanti:
# processor = SignalProcessor(sample_rate=256)
# clean_data = processor.apply_filter(raw_eeg_data)