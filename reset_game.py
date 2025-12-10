import time
from game_state import GameState
from config import GAME_DURATION
import random
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
