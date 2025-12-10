import os
import pyaudio

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