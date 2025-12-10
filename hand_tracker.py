import cv2
import mediapipe as mp
import numpy as np

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
