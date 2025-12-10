import cv2
import numpy as np
import time
from config import COLOR_SKY, COLOR_GROUND, COLOR_POLE, COLOR_BACKBOARD, COLOR_RIM, COLOR_NET, COLOR_PLAYER_BODY, COLOR_PLAYER_SHIRT

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
