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
from config import *
from audio_processor import AudioProcessor
from hand_tracker import HandTracker
from ball import Ball
from renderer import GameRenderer
from audio_player import AudioPlayer
from game_state import GameState
from reset_game import reset_game_state
from kernel_video import enhance_frame
# @dataclass
# class GameState:
#     score: int = 0
#     miss: int = 0
#     best_score: int = 0
#     shooting: bool = False
#     target_accuracy: int = field(default_factory=lambda: random.randint(40, 95))
#     ball: Optional["Ball"] = None
#     game_active: bool = False
#     game_over: bool = False
#     start_time: float = 0.0
#     remaining_time: float = GAME_DURATION
#     last_shot_accuracy: Optional[float] = None
#     shot_result: Optional[str] = None
#     result_display_time: float = 0.0

# Pemrosesan Audio dan ekstraksi level suara
# ==================== BALL ====================

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