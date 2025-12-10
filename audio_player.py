import os
import pygame
from config import BGM_FILE, SFX_SCORE, SFX_MISS, SFX_BEST
try:
    import pygame
    _HAS_PYGAME = True
except Exception:
    _HAS_PYGAME = False
    print("⚠️ pygame not available: audio playback will be limited. Install pygame for SFX/BGM.")

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
