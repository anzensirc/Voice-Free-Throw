import random
import time
from dataclasses import dataclass, field
from typing import Optional
from config import GAME_DURATION
from ball import Ball

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

