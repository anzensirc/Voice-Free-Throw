import threading
from collections import deque
import numpy as np
import pyaudio
from config import RATE, CHUNK, FORMAT, CHANNELS, BAND_LOW, BAND_HIGH
class AudioProcessor:
    """
    Mengambil input audio dari mikrofon → melakukan bandpass FFT → menghitung level suara 0..100.
    Digunakan sebagai indikator kekuatan suara pemain untuk menembak bola.
    """
    def __init__(self, rate=RATE, chunk=CHUNK):
        self._pa = pyaudio.PyAudio()
        self.stream = None
        self.running = False
        self.level = 0.0  # smoothed audio level 0..100
        self._buffer = deque(maxlen=8)
        self.rate = rate
        self.chunk = chunk

    def start(self):
        """Memulai stream audio dan thread background untuk memproses audio real-time."""
        try:
            self.stream = self._pa.open(format=FORMAT, channels=CHANNELS, rate=self.rate,
                                       input=True, frames_per_buffer=self.chunk)
            self.running = True
            thread = threading.Thread(target=self._process_audio, daemon=True)
            thread.start()
            print("✓ Audio capture initialized")
        except Exception as e:
            print("✗ Failed to open microphone:", e)
            self.running = False

    def stop(self):
        """Menghentikan stream mikrofon dan melepaskan resource PyAudio."""
        self.running = False
        try:
            if self.stream:
                self.stream.stop_stream()
                self.stream.close()
        finally:
            try:
                self._pa.terminate()
            except Exception:
                pass

    @staticmethod
    def bandpass_fft(signal: np.ndarray, fs: int, low: float, high: float) -> np.ndarray:
        """ Bandpass filter berbasis FFT:
        - Menghilangkan frekuensi di luar rentang 300–3000Hz
        - Mengurangi noise DC, angin, suara rendah/tajam """

        n = len(signal)
        if n == 0:
            return signal
        freqs = np.fft.rfftfreq(n, d=1.0/fs)
        spectrum = np.fft.rfft(signal)
        mask = (freqs >= low) & (freqs <= high)
        spectrum[~mask] = 0
        filtered = np.fft.irfft(spectrum, n=n)
        return filtered

    def _process_audio(self):
        """
        Thread audio:
        - Membaca chunk suara
        - Bandpass FFT
        - Hitung RMS energy
        - Normalisasi menjadi level 0–100
        - Smoothing menggunakan moving average buffer
        """        
        SCALE_DIV = 300.0

        while self.running:
            try:
                raw = self.stream.read(self.chunk, exception_on_overflow=False)
                data = np.frombuffer(raw, dtype=np.int16).astype(np.float32)
                filtered = AudioProcessor.bandpass_fft(data, self.rate, BAND_LOW, BAND_HIGH)
                energy = np.sqrt(np.mean(filtered**2)) if filtered.size > 0 else 0.0
                normalized = min(100.0, (energy / SCALE_DIV) * 100.0)
                self._buffer.append(normalized)
                self.level = float(sum(self._buffer) / len(self._buffer))
            except Exception:
                pass
