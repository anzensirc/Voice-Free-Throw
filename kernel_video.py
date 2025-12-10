from typing import Tuple
import cv2
import numpy as np

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
