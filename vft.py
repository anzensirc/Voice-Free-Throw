import os
import time
import random
import threading
from collections import deque
from dataclasses import dataclass, field
from typing import Optional, List, Tuple
import cv2
import mediapipe as mp
import numpy as np
import pyaudio

#Mengimport pygame jika tersedia
try:
    import pygame
    _HAS_PYGAME = True
except Exception:
    _HAS_PYGAME = False
    print("⚠️ pygame not available: audio playback will be limited. Install pygame for SFX/BGM.")

#Config Layar
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
FPS = 60

# Config Audio Capture
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100  # sampling rate

# Timing dan fisika bola
GRAVITY = 1200.0
FLIGHT_TIME = 1.0
GAME_DURATION = 60

# Warna pada Layout Objek Game
COLOR_SKY = (240, 200, 150)
COLOR_GROUND = (100, 150, 50)
COLOR_POLE = (50, 50, 150)
COLOR_BACKBOARD = (220, 220, 220)
COLOR_RIM = (0, 0, 255)
COLOR_NET = (200, 200, 200)
COLOR_BALL = (0, 140, 255)
COLOR_PLAYER_BODY = (180, 130, 70)
COLOR_PLAYER_SHIRT = (0, 180, 255)

# Path untuk audio yang dipakai (sfx dan bgm)
ASSET_DIR = os.path.join(os.path.dirname(__file__), "assets")
BGM_FILE = os.path.join(ASSET_DIR, "bgm.wav")
SFX_SCORE = os.path.join(ASSET_DIR, "score.wav")
SFX_MISS = os.path.join(ASSET_DIR, "miss.wav")
SFX_BEST = os.path.join(ASSET_DIR, "best.wav")

# Batas frekuensi untuk bandpass filter audio
BAND_LOW = 300.0
BAND_HIGH = 3000.0

# Inisialisasi state game
@dataclass
class GameState:
    score: int = 0
    miss: int = 0
    best_score: int = 0
    shooting: bool = False
    target_accuracy: int = field(default_factory=lambda: random.randint(40, 95))
    ball: Optional["Ball"] = None
    game_active: bool = False
    game_over: bool = False
    start_time: float = 0.0
    remaining_time: float = GAME_DURATION
    last_shot_accuracy: Optional[float] = None
    shot_result: Optional[str] = None
    result_display_time: float = 0.0

# Pemrosesan Audio dan ekstraksi level suara
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

class HandTracker:
    """Menggunakan Mediapipe Hands untuk deteksi gesture open–close sebagai trigger tembakan."""
    def __init__(self):
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(max_num_hands=1,
                                         min_detection_confidence=0.7,
                                         min_tracking_confidence=0.5)
        self.mp_draw = mp.solutions.drawing_utils
        self._last_open = False
        self._last_closed = False

    def process(self, frame: np.ndarray) -> bool:
        """
        - Memproses frame untuk deteksi tangan
        - Menggambar landmark
        - Mendapatkan bounding box
        - Mendeteksi transisi gesture open→close→open untuk dianggap 'shoot'
        """
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.hands.process(rgb)

        if not results.multi_hand_landmarks:
            self._last_open = False
            self._last_closed = False
            return False

        landmarks = results.multi_hand_landmarks[0]
        self.mp_draw.draw_landmarks(frame, landmarks, self.mp_hands.HAND_CONNECTIONS)

        h, w, _ = frame.shape
        xs = [lm.x for lm in landmarks.landmark]
        ys = [lm.y for lm in landmarks.landmark]
        x1, x2 = int(min(xs) * w), int(max(xs) * w)
        y1, y2 = int(min(ys) * h), int(max(ys) * h)
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

        is_open = self._is_hand_open(landmarks.landmark)
        is_closed = self._is_hand_closed(landmarks.landmark)

        shoot = False
        if is_open and not self._last_open and self._last_closed:
            shoot = True

        self._last_open = is_open
        self._last_closed = is_closed
        return shoot

    @staticmethod
    def _is_hand_open(landmarks) -> bool:
        """Deteksi tangan terbuka berdasarkan posisi jari tip vs pip"""
        tips = [8, 12, 16, 20]
        pips = [6, 10, 14, 18]
        extended = sum(1 for t, p in zip(tips, pips) if landmarks[t].y < landmarks[p].y)
        thumb_extended = abs(landmarks[4].x - landmarks[2].x) > 0.05
        return (extended >= 3) and thumb_extended

    @staticmethod
    def _is_hand_closed(landmarks) -> bool:
        """Deteksi tangan mengepal berdasarkan kedekatan jari dengan posisi telapak."""
        tips = [8, 12, 16, 20]
        palm_y = landmarks[0].y
        closed_count = sum(1 for t in tips if abs(landmarks[t].y - palm_y) < 0.12)
        return closed_count >= 3

# ==================== BALL ====================
class Ball:
    """Objek bola basket: posisi, gravitasi, scoring chance, dan trajectory."""
    def __init__(self, start_x: float, start_y: float, target_x: float, target_y: float, current_accuracy: float, target_accuracy: float):
        self.x = float(start_x)
        self.y = float(start_y)
        self.radius = 18
        self.active = True
        self.trajectory: List[Tuple[int, int]] = []
        self.final_accuracy = float(current_accuracy)
        self.will_score = self._determine_score_chance(self.final_accuracy)
        self._setup_trajectory(target_x, target_y, target_accuracy)

    def _determine_score_chance(self, a: float) -> bool:
        """
        Menentukan probabilitas bola masuk berdasarkan akurasi suara.
        Semakin tinggi akurasi, semakin besar peluang score.
        """
        if a < 75:
            return False
        if 75 <= a <= 80:
            return random.random() < 0.70
        if 81 <= a <= 84:
            return random.random() < 0.80
        if 85 <= a <= 90:
            return random.random() < 0.85
        if 91 <= a <= 95:
            return random.random() < 0.90
        return True

    def _setup_trajectory(self, tx, ty, target_accuracy):
        """
        Menghitung lintasan bola:
        - Jika akurasi rendah: undershoot (bola kurang sampai)
        - Jika akurasi menengah: sedikit error acak
        - Jika akurasi tinggi: lintasan lebih ideal
        """
        actual = self.final_accuracy
        adjusted_x, adjusted_y = tx, ty
        if actual < 75:
            undershoot = (75 - actual) * 5
            adjusted_x = tx - undershoot - 50
            adjusted_y = ty + 30
        elif actual <= 100:
            max_error = (100 - actual) * 0.8
            if self.will_score:
                adjusted_x = tx + random.uniform(-max_error * 0.3, max_error * 0.3)
                adjusted_y = ty
            else:
                adjusted_x = tx + random.uniform(-max_error * 2, max_error * 2)
                adjusted_y = ty + random.uniform(-10, 15)
        else:
            overshoot = (actual - 100) * 4
            adjusted_x = tx + overshoot + 30
            adjusted_y = ty - 20

        dx = adjusted_x - self.x
        dy = adjusted_y - self.y
        t = FLIGHT_TIME
        g = GRAVITY
        self.vx = dx / t
        self.vy = (dy - 0.5 * g * t * t) / t

    def update(self, dt: float, basket_x: float, basket_y: float, basket_rim_radius: float) -> Optional[str]:
        """
        Update posisi bola:
        - Integrasi fisika vx, vy, gravitasi
        - Deteksi tabrakan rim & score
        - Jika keluar layar → miss
        """
        if not self.active:
            return None
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vy += GRAVITY * dt

        self.trajectory.append((int(self.x), int(self.y)))
        if len(self.trajectory) > 15:
            self.trajectory.pop(0)

        if basket_y - self.radius <= self.y <= basket_y + 30:
            dist = abs(self.x - basket_x)
            if dist < basket_rim_radius:
                if self.will_score and self.vy > 0:
                    self.active = False
                    return "score"
                elif not self.will_score and dist < (basket_rim_radius - 5):
                    self.vy = -abs(self.vy) * 0.3
                    self.vx += random.uniform(-100, 100)

        if self.x > SCREEN_WIDTH + 50 or self.x < -50 or self.y > SCREEN_HEIGHT + 50:
            self.active = False
            return "miss"
        return None

    def draw(self, frame: np.ndarray):
        """Menggambar bola dan bayangan serta jejak lintasan."""
        if not self.active:
            return
        shadow_y = SCREEN_HEIGHT - 80
        cv2.ellipse(frame, (int(self.x), shadow_y), (self.radius, 5), 0, 0, 360, (100, 100, 100), -1)
        for i in range(len(self.trajectory) - 1):
            alpha = i / max(1, len(self.trajectory))
            thickness = int(2 + alpha * 3)
            cv2.line(frame, self.trajectory[i], self.trajectory[i + 1], COLOR_BALL, thickness)
        cv2.circle(frame, (int(self.x), int(self.y)), self.radius, COLOR_BALL, -1)
        cv2.circle(frame, (int(self.x - 5), int(self.y - 5)), int(self.radius * 0.6), (0, 180, 255), -1)
        cv2.circle(frame, (int(self.x), int(self.y)), self.radius, (0, 0, 0), 2)

class GameRenderer:
    """Renderer utama untuk latar, ring, pemain, UI, dan indikator akurasi suara."""    
    def __init__(self, width: int, height: int):    
        self.width = width
        self.height = height
        self.ground_y = height - 120
        self.player_x = int(width * 0.15)
        self.player_y = self.ground_y - 120
        self.basket_x = int(width * 0.70)
        self.basket_y = int(height * 0.35)
        self.basket_rim_radius = 50

    def draw_background(self, frame: np.ndarray):
        """Menggambar langit, tanah, dan garis-garis lapangan."""
        cv2.rectangle(frame, (0, 0), (self.width, self.ground_y), COLOR_SKY, -1)
        cv2.rectangle(frame, (0, self.ground_y), (self.width, self.height), COLOR_GROUND, -1)
        for x in range(0, self.width, 100):
            cv2.line(frame, (x, self.ground_y), (x, self.height), (80, 130, 40), 2)

    def draw_basket(self, frame: np.ndarray):
        """Menggambar tiang ring, papan, ring, dan jaring."""
        pole_x = self.basket_x + 60
        cv2.rectangle(frame, (pole_x - 8, self.basket_y - 80), (pole_x + 8, self.ground_y), COLOR_POLE, -1)
        cv2.rectangle(frame, (pole_x - 5, self.basket_y - 90), (pole_x + 15, self.basket_y + 40), COLOR_BACKBOARD, -1)
        cv2.ellipse(frame, (self.basket_x, self.basket_y), (self.basket_rim_radius, 15), 0, 0, 180, COLOR_RIM, 5)
        for i in range(10):
            angle = i * 18
            x1 = int(self.basket_x + self.basket_rim_radius * np.cos(np.radians(angle)))
            y1 = self.basket_y
            x2 = int(self.basket_x + (self.basket_rim_radius - 10) * np.cos(np.radians(angle)))
            y2 = self.basket_y + 40
            cv2.line(frame, (x1, y1), (x2, y2), COLOR_NET, 2)

    def draw_player(self, frame: np.ndarray, hand_ready: bool):
        """Menggambar pemain dengan animasi tangan siap atau tidak siap menembak."""
        x, y = self.player_x, self.player_y
        cv2.ellipse(frame, (x, self.ground_y - 5), (35, 10), 0, 0, 360, (100, 100, 100), -1)
        cv2.line(frame, (x - 15, y + 40), (x - 15, y + 80), COLOR_PLAYER_BODY, 10)
        cv2.line(frame, (x + 15, y + 40), (x + 15, y + 80), COLOR_PLAYER_BODY, 10)
        cv2.rectangle(frame, (x - 25, y), (x + 25, y + 50), COLOR_PLAYER_SHIRT, -1)
        cv2.rectangle(frame, (x - 25, y), (x + 25, y + 50), (0, 0, 0), 2)
        if hand_ready:
            cv2.line(frame, (x - 25, y + 10), (x - 50, y - 30), COLOR_PLAYER_BODY, 8)
            cv2.line(frame, (x + 25, y + 10), (x + 50, y + 20), COLOR_PLAYER_BODY, 8)
        else:
            cv2.line(frame, (x - 25, y + 10), (x - 45, y + 40), COLOR_PLAYER_BODY, 8)
            cv2.line(frame, (x + 25, y + 10), (x + 45, y + 40), COLOR_PLAYER_BODY, 8)
        cv2.circle(frame, (x, y - 20), 22, COLOR_PLAYER_BODY, -1)
        cv2.circle(frame, (x, y - 20), 22, (0, 0, 0), 2)
        cv2.circle(frame, (x - 8, y - 23), 3, (0, 0, 0), -1)
        cv2.circle(frame, (x + 8, y - 23), 3, (0, 0, 0), -1)

    def draw_accuracy_bar(self, frame: np.ndarray, target_accuracy: int, current_level: float):
        """
        Membuat vertical bar level suara:
        - Warna gradasi dari merah → kuning → hijau
        - Target zone (kotak hijau)
        - Akurasi dihitung dari jarak target vs level suara
        """
        bar_w, bar_h = 35, 300
        x = 55
        y = (self.height - bar_h) // 2
        cv2.rectangle(frame, (x - 15, y - 40), (x + bar_w + 15, y + bar_h + 40), (0, 0, 0), -1)
        cv2.rectangle(frame, (x - 15, y - 40), (x + bar_w + 15, y + bar_h + 40), (255, 255, 255), 3)
        cv2.putText(frame, "VOLUME", (x - 10, y - 50), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
        cv2.rectangle(frame, (x, y), (x + bar_w, y + bar_h), (255, 255, 255), 3)
        fill_h = int((current_level / 100.0) * bar_h)
        for i in range(fill_h):
            ratio = i / max(1, bar_h)
            if ratio < 0.33:
                color = (0, int(50 + 205 * (ratio / 0.33)), 255)
            elif ratio < 0.66:
                color = (0, 255, int(255 - 255 * ((ratio - 0.33) / 0.33)))
            else:
                color = (0, 255, 0)
            cv2.line(frame, (x, y + bar_h - i), (x + bar_w, y + bar_h - i), color, 1)
        t_y = y + bar_h - int((target_accuracy / 100.0) * bar_h)
        zone = 8
        cv2.rectangle(frame, (x - 10, t_y - zone), (x + bar_w + 10, t_y + zone), (0, 255, 0), -1)
        cv2.rectangle(frame, (x - 10, t_y - zone), (x + bar_w + 10, t_y + zone), (0, 200, 0), 2)
        # cv2.putText(frame, f"{int(current_level)}%", (x + 5, y + bar_h + 25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (122, 255, 255), 1)
        diff = abs(target_accuracy - current_level)
        accuracy = max(0, int(100 - diff))
        if accuracy >= 90:
            acc_color, acc_text = (0, 255, 0), "SEMPURNA!"
        elif accuracy >= 75:
            acc_color, acc_text = (0, 255, 255), "BAGUS!"
        elif accuracy >= 50:
            acc_color, acc_text = (0, 165, 255), "CUKUP"
        else:
            acc_color, acc_text = (0, 0, 255), "KURANG"
        cv2.putText(frame, f"{accuracy}%", (x - 5, y + bar_h + 55), cv2.FONT_HERSHEY_SIMPLEX, 0.6, acc_color, 2)
        cv2.putText(frame, acc_text, (x - 10, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.45, acc_color, 2)

    def draw_hand_status(self, frame: np.ndarray, hand_ready: bool, shooting: bool):
        """Menampilkan status tangan: TAHAN / BUKA TANGAN / SHOOTING!"""
        x, y = 50, 40
        cv2.rectangle(frame, (x - 10, y - 10), (x + 180, y + 80), (0, 0, 0), -1)
        cv2.rectangle(frame, (x - 10, y - 10), (x + 180, y + 80), (255, 255, 255), 2)
        if shooting:
            status, color = "SHOOTING!", (0, 255, 255)
        elif hand_ready:
            status, color = "TAHAN", (0, 255, 0)
        else:
            status, color = "BUKA TANGAN", (200, 200, 200)
        cv2.putText(frame, "STATUS:", (x, y + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.putText(frame, status, (x, y + 50), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

    def draw_controls_panel(self, frame: np.ndarray, time_remaining: float, score: int, miss: int, best_score: int):
        """Menampilkan panel kontrol: waktu, skor, miss, best score, instruksi tombol."""
        x = self.width - 280
        y = 20
        cv2.rectangle(frame, (x, y), (x + 260, y + 180), (0, 0, 0), -1)
        cv2.rectangle(frame, (x, y), (x + 260, y + 180), (255, 255, 255), 3)
        minutes = int(time_remaining // 60)
        seconds = int(time_remaining % 60)
        timer_color = (0, 255, 0) if time_remaining > 10 else (0, 0, 255)
        cv2.putText(frame, f"TIME: {minutes:02d}:{seconds:02d}", (x + 20, y + 35), cv2.FONT_HERSHEY_SIMPLEX, 0.8, timer_color, 2)
        cv2.putText(frame, f"SCORE: {score}", (x + 20, y + 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(frame, f"MISS: {miss}", (x + 20, y + 100), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        cv2.putText(frame, f"BEST: {best_score}", (x + 20, y + 130), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 215, 0), 2)
        cv2.putText(frame, "Q: QUIT | R: RESTART", (x + 10, y + 165), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1)

    def draw_shot_result(self, frame: np.ndarray, accuracy: float, result: str, display_time: float):
        """Menampilkan hasil tembakan: SCORE! atau MISS! dengan efek fade out."""
        if time.time() - display_time < 2.0:
            alpha = max(0.0, 1.0 - (time.time() - display_time) / 2.0)
            x = self.width // 2
            y = 150
            if result == "score":
                text = f"SCORE! Akurasi: {int(accuracy)}%"
                color = (0, 255, 0)
            else:
                text = f"MISS! Akurasi: {int(accuracy)}%"
                color = (0, 0, 255)
            fade_color = (int(color[0] * alpha), int(color[1] * alpha), int(color[2] * alpha))
            cv2.putText(frame, text, (x - 150, y), cv2.FONT_HERSHEY_SIMPLEX, 1.2, fade_color, 3)

    def draw_game_over(self, frame: np.ndarray, score: int, best_score: int):
        """Menampilkan layar Game Over dengan skor akhir dan instruksi restart/quit."""
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (self.width, self.height), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)

        # Judul Game Over
        cv2.putText(frame, "GAME OVER!", (self.width // 2 - 200, 200),
                    cv2.FONT_HERSHEY_SIMPLEX, 2.0, (0, 0, 255), 4)

        # Score
        cv2.putText(frame, f"Final Score: {score}", (self.width // 2 - 150, 280),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.4, (255, 255, 255), 3)
        cv2.putText(frame, f"Best Score: {best_score}", (self.width // 2 - 150, 330),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.4, (255, 215, 0), 3)

        # Instruksi permainan (seperti start screen)
        cv2.putText(frame, "Instruksi Bermain:", (self.width // 2 - 200, 400),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 255), 3)

        cv2.putText(frame, "1. Buka tangan untuk siap", (self.width // 2 - 230, 450),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (200, 200, 200), 2)
        cv2.putText(frame, "2. Sesuaikan volume dengan target", (self.width // 2 - 230, 485),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (200, 200, 200), 2)
        cv2.putText(frame, "3. Kepal tangan untuk menahan", (self.width // 2 - 230, 520),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (200, 200, 200), 2)
        cv2.putText(frame, "4. Buka lagi untuk melempar", (self.width // 2 - 230, 555),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (200, 200, 200), 2)

        # Tombol restart / quit
        cv2.putText(frame, "Press 'R' to Restart or 'Q' to Quit",
                    (self.width // 2 - 260, 620),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)

    def draw_start_screen(self, frame: np.ndarray):
        """Menampilkan layar awal dengan instruksi permainan."""
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (self.width, self.height), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)
        cv2.putText(frame, "VOICE FREE THROW", (self.width // 2 - 300, 200), cv2.FONT_HERSHEY_SIMPLEX, 2.0, (0, 255, 255), 4)
        cv2.putText(frame, "Instruksi:", (self.width // 2 - 150, 300), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 2)
        cv2.putText(frame, "1. Buka tangan untuk siap", (self.width // 2 - 200, 350), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (200, 200, 200), 2)
        cv2.putText(frame, "2. Sesuaikan volume dengan target", (self.width // 2 - 200, 390), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (200, 200, 200), 2)
        cv2.putText(frame, "3. Kepal tangan untuk menahan", (self.width // 2 - 200, 430), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (200, 200, 200), 2)
        cv2.putText(frame, "4. Buka lagi untuk melempar", (self.width // 2 - 200, 470), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (200, 200, 200), 2)
        cv2.putText(frame, "Press 'SPACE' to Start", (self.width // 2 - 180, 560), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)

def reset_game_state(state: GameState):
    """Mengatur ulang status permainan untuk memulai ulang."""
    if state.score > state.best_score:
        state.best_score = state.score
    state.score = 0
    state.miss = 0
    state.shooting = False
    state.ball = None
    state.game_active = True
    state.game_over = False
    state.start_time = time.time()
    state.remaining_time = GAME_DURATION
    state.target_accuracy = random.randint(40, 95)
    state.last_shot_accuracy = None
    state.shot_result = None
    state.result_display_time = 0.0

def enhance_frame(frame: np.ndarray) -> np.ndarray:
    """Meningkatkan frame kamera untuk pelacakan tangan yang lebih baik:
    1. Mengurangi noise dengan Gaussian Blur
    2. Unsharp Mask / Sharpen
    3. Contrast & Brightness Tweak
    4. Auto-White-Balance (Gray World Approximation)
    """
    # noise reduction
    frame = cv2.GaussianBlur(frame, (3, 3), 0)
    # unsharp mask / sharpen
    kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
    frame = cv2.filter2D(frame, -1, kernel)
    # contrast & brightness tweak
    frame = cv2.convertScaleAbs(frame, alpha=1.12, beta=8)
    # simple auto-white-balance (gray-world approximation)
    try:
        b, g, r = cv2.split(frame.astype(np.float32))
        avg = (np.mean(b) + np.mean(g) + np.mean(r)) / 3.0
        b = np.clip(b * (avg / (np.mean(b) + 1e-6)), 0, 255)
        g = np.clip(g * (avg / (np.mean(g) + 1e-6)), 0, 255)
        r = np.clip(r * (avg / (np.mean(r) + 1e-6)), 0, 255)
        frame = cv2.merge([b, g, r]).astype(np.uint8)
    except Exception:
        pass
    return frame

class AudioPlayer:
    """Manajemen audio menggunakan pygame:
    1. Inisialisasi pygame mixer
    2. Memuat musik dan efek suara
    3. Mengatur volume efek suara
    """
    def __init__(self):
        self.has_audio = _HAS_PYGAME
        self.bgm = None
        self.sfx_score = None
        self.sfx_miss = None
        self.sfx_best = None
        if self.has_audio:
            try:
                pygame.mixer.init()
                # Memuat file audio dengan pengecekan aman
                self.bgm = self._safe_load(BGM_FILE)
                self.sfx_score = self._safe_load(SFX_SCORE)
                self.sfx_miss = self._safe_load(SFX_MISS)
                self.sfx_best = self._safe_load(SFX_BEST)
                if self.bgm:
                    self.bgm.set_volume(0.4)
                for s in (self.sfx_score, self.sfx_miss, self.sfx_best):
                    if s:
                        s.set_volume(0.9)
                print("✓ pygame audio initialized")
            except Exception as e:
                print("✗ pygame init error:", e)
                self.has_audio = False

    def _safe_load(self, path):
        if os.path.isfile(path):
            try:
                return pygame.mixer.Sound(path)
            except Exception as e:
                print(f"✗ failed to load {path}: {e}")
                return None
        else:
            print(f"⚠️ audio file not found: {path}")
            return None

    def play_bgm(self):
        if self.has_audio and self.bgm:
            self.bgm.play(loops=-1)

    def stop_bgm(self):
        if self.has_audio and self.bgm:
            self.bgm.stop()

    def play_score(self):
        if self.has_audio and self.sfx_score:
            self.sfx_score.play()

    def play_miss(self):
        if self.has_audio and self.sfx_miss:
            self.sfx_miss.play()

    def play_best(self):
        if self.has_audio and self.sfx_best:
            self.sfx_best.play()

    def quit(self):
        if self.has_audio:
            try:
                pygame.mixer.quit()
            except Exception:
                pass
def main():
    """Fungsi utama untuk menjalankan game Voice Free Throw."""
    audio_cap = AudioProcessor()
    audio_cap.start()

    audio_player = AudioPlayer()
    if audio_player.has_audio:
        audio_player.play_bgm()

    hand_tracker = HandTracker()
    renderer = GameRenderer(SCREEN_WIDTH, SCREEN_HEIGHT)
    state = GameState()

    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    cv2.namedWindow('Voice Free Throw', cv2.WINDOW_NORMAL)
    cv2.resizeWindow('Voice Free Throw', SCREEN_WIDTH, SCREEN_HEIGHT)

    last_time = time.time()
    print("\n✓ Game ready! Press SPACE to start. Q: Quit | R: Restart")

    try:
        while True:
            ret, raw_frame = cap.read()
            if not ret:
                print("✗ Camera read failed.")
                break

            # proses frame untuk pelacakan tangan
            hand_frame = enhance_frame(raw_frame.copy())

            # delta waktu untuk update game
            now = time.time()
            dt = now - last_time
            last_time = now
            if dt <= 0:
                dt = 1.0 / FPS

            # update timer
            if state.game_active and not state.game_over:
                elapsed = now - state.start_time
                state.remaining_time = max(0.0, GAME_DURATION - elapsed)
                if state.remaining_time <= 0:
                    state.game_active = False
                    state.game_over = True
                    if state.score > state.best_score:
                        state.best_score = state.score
                        #memutar sfx best score
                        audio_player.play_best()

            # pendeteksian tangan
            should_shoot = hand_tracker.process(hand_frame)

            # menembak bola jika kondisi terpenuhi
            if should_shoot and not state.shooting and state.game_active and not state.game_over:
                state.shooting = True
                audio_level = audio_cap.level
                diff = abs(state.target_accuracy - audio_level)
                current_accuracy = max(0.0, 100.0 - diff)
                state.last_shot_accuracy = current_accuracy
                # buat objek bola baru
                state.ball = Ball(renderer.player_x + 30, renderer.player_y - 20, renderer.basket_x, renderer.basket_y, current_accuracy, state.target_accuracy)

            #  rendering frame
            frame = np.zeros((SCREEN_HEIGHT, SCREEN_WIDTH, 3), dtype=np.uint8)
            renderer.draw_background(frame)
            renderer.draw_basket(frame)
            renderer.draw_player(frame, hand_ready=not state.shooting)

            # update dan gambar bola jika ada
            if state.ball and state.ball.active:
                result = state.ball.update(dt, renderer.basket_x, renderer.basket_y, renderer.basket_rim_radius)
                state.ball.draw(frame)
                if result == "score":
                    state.score += 1
                    state.shooting = False
                    state.ball = None
                    state.target_accuracy = random.randint(40, 95)
                    state.shot_result = "score"
                    state.result_display_time = now
                    audio_player.play_score()
                    # cek best score
                    if state.score > state.best_score:
                        state.best_score = state.score
                        audio_player.play_best()
                elif result == "miss":
                    state.miss += 1
                    state.shooting = False
                    state.ball = None
                    state.target_accuracy = random.randint(40, 95)
                    state.shot_result = "miss"
                    state.result_display_time = now
                    audio_player.play_miss()

            # UI
            if state.game_active and not state.game_over:
                if not state.shooting:
                    renderer.draw_accuracy_bar(frame, state.target_accuracy, audio_cap.level)
                renderer.draw_hand_status(frame, hand_ready=not state.shooting, shooting=state.shooting)
                if state.last_shot_accuracy is not None and state.shot_result:
                    renderer.draw_shot_result(frame, state.last_shot_accuracy, state.shot_result, state.result_display_time)

            renderer.draw_controls_panel(frame, state.remaining_time, state.score, state.miss, state.best_score)

            # overlay
            if not state.game_active:
                if state.game_over:
                    renderer.draw_game_over(frame, state.score, state.best_score)
                else:
                    renderer.draw_start_screen(frame)

            # preview tangan
            try:
                preview = cv2.resize(hand_frame, (220, 165))
                frame[SCREEN_HEIGHT - 185:SCREEN_HEIGHT - 20, SCREEN_WIDTH - 240:SCREEN_WIDTH - 20] = preview
                cv2.rectangle(frame, (SCREEN_WIDTH - 240, SCREEN_HEIGHT - 185), (SCREEN_WIDTH - 20, SCREEN_HEIGHT - 20), (0, 255, 0), 2)
            except Exception:
                pass
            cv2.imshow('Voice Free Throw', frame)

            # keyboard input
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('r'):
                reset_game_state(state)
            elif key == ord(' ') and not state.game_active and not state.game_over:
                reset_game_state(state)

    finally:
        # cleanup
        audio_cap.stop()
        audio_player.stop_bgm()
        audio_player.quit()
        cap.release()
        cv2.destroyAllWindows()
        print("\n✓ Game ended. Best Score:", state.best_score)

if __name__ == "__main__":
    main()