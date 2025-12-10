import random
from typing import List, Tuple, Optional
import cv2
from config import SCREEN_WIDTH, SCREEN_HEIGHT, GRAVITY, FLIGHT_TIME, COLOR_BALL
import numpy as np
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
