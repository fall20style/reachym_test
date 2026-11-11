from reachy_mini import ReachyMini
from reachy_mini.motion.recorded_move import RecordedMoves

moves = RecordedMoves("pollen-robotics/reachy-mini-emotions-library")
with ReachyMini() as mini:
    mini.play_move(moves.get("happy"), initial_goto_duration=1.0)
