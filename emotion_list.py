from reachy_mini.motion.recorded_move import RecordedMoves

moves = RecordedMoves("pollen-robotics/reachy-mini-emotions-library")
print(moves.list_moves())  # 사용 가능한 모든 모션 이름 출력
