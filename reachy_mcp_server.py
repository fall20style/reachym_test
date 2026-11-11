import os
import sys
import json
import time
import contextlib
import numpy as np
from mcp.server.mcpserver import MCPServer
from reachy_mini import ReachyMini
from reachy_mini.utils import create_head_pose
from reachy_mini.motion.recorded_move import RecordedMoves

mcp = MCPServer("ReachyMiniFullController")
_mini: ReachyMini | None = None
_recorded_trajectory = None
_emotion_lib = None
_dance_lib = None


def get_mini() -> ReachyMini:
    """ReachyMini 클라이언트를 지연 초기화하며 stdout 오염을 방지합니다."""
    global _mini
    if _mini is None:
        with contextlib.redirect_stdout(sys.stderr):
            _mini = ReachyMini()
    return _mini


# ==========================================
# 1. 기본 및 정밀 관절 제어 (Kinematics)
# ==========================================

@mcp.tool()
def move_head_and_body(
    x: float = 0.0,
    y: float = 0.0,
    z: float = 0.0,
    roll: float = 0.0,
    pitch: float = 0.0,
    yaw: float = 0.0,
    body_yaw: float = 0.0,
    left_antenna: float = 0.0,
    right_antenna: float = 0.0,
    duration: float = 1.0,
    method: str = "minjerk",
) -> str:
    """로봇의 머리 위치(mm), 회전(deg), 몸통 회전(deg), 양쪽 안테나(rad)를 정밀 제어합니다."""
    mini = get_mini()
    mini.goto_target(
        head=create_head_pose(x=x, y=y, z=z, roll=roll, pitch=pitch, yaw=yaw, degrees=True, mm=True),
        body_yaw=np.deg2rad(body_yaw),
        antennas=[left_antenna, right_antenna],
        duration=duration,
        method=method,
    )
    return f"이동 완료: pos=({x},{y},{z})mm, rot=({roll},{pitch},{yaw})deg, body={body_yaw}deg"


@mcp.tool()
def look_at_3d_point(x: float, y: float, z: float, duration: float = 0.8) -> str:
    """로봇 기준 3D 공간 좌표(미터 단위: x=앞, y=왼쪽, z=위)를 향해 고개와 몸통을 돌려 응시합니다."""
    mini = get_mini()
    mini.look_at_world(x=x, y=y, z=z, duration=duration)
    return f"3D 좌표 ({x}, {y}, {z}) 응시 완료"


@mcp.tool()
def look_at_camera_pixel(u: int, v: int, duration: float = 0.6) -> str:
    """카메라 이미지 상의 특정 픽셀 좌표(u, v)가 시야 중앙에 오도록 고개를 돌립니다."""
    mini = get_mini()
    mini.look_at_image(u=u, v=v, duration=duration)
    return f"이미지 픽셀 ({u}, {v}) 응시 완료"


@mcp.tool()
def reset_pose(duration: float = 0.8) -> str:
    """고개, 몸통, 안테나를 모두 초기 정면 자세로 복귀시킵니다."""
    mini = get_mini()
    mini.goto_target(
        head=create_head_pose(),
        antennas=[0.0, 0.0],
        body_yaw=0.0,
        duration=duration,
    )
    return "기본 정면 자세로 복귀했습니다."


# ==========================================
# 2. 공식 감정 및 춤 모션 라이브러리
# ==========================================

@mcp.tool()
def list_official_moves(category: str = "emotions") -> str:
    """Hugging Face 공식 모션 라이브러리의 동작 이름 목록을 조회합니다. ('emotions' 또는 'dances')"""
    global _emotion_lib, _dance_lib
    with contextlib.redirect_stdout(sys.stderr):
        if category == "dances":
            if _dance_lib is None:
                _dance_lib = RecordedMoves("pollen-robotics/reachy-mini-dances-library")
            return f"사용 가능한 춤 목록: {_dance_lib.list_moves()}"
        else:
            if _emotion_lib is None:
                _emotion_lib = RecordedMoves("pollen-robotics/reachy-mini-emotions-library")
            return f"사용 가능한 감정 목록: {_emotion_lib.list_moves()}"


@mcp.tool()
def play_official_move(move_name: str, category: str = "emotions") -> str:
    """공식 감정 또는 춤 동작을 실행합니다."""
    global _emotion_lib, _dance_lib
    mini = get_mini()
    with contextlib.redirect_stdout(sys.stderr):
        if category == "dances":
            if _dance_lib is None:
                _dance_lib = RecordedMoves("pollen-robotics/reachy-mini-dances-library")
            move = _dance_lib.get(move_name)
        else:
            if _emotion_lib is None:
                _emotion_lib = RecordedMoves("pollen-robotics/reachy-mini-emotions-library")
            move = _emotion_lib.get(move_name)

    mini.play_move(move, initial_goto_duration=0.8)
    return f"공식 모션 '{move_name}' ({category}) 재생 완료"


# ==========================================
# 3. 목적별 복합 동작 시나리오 (.cfg) 실행 도구
# ==========================================

@mcp.tool()
def list_scenarios() -> str:
    """현재 작업 폴더 및 scenarios/ 폴더에 있는 목적별 시나리오(.cfg) 파일 목록과 설명(첫 줄 주석)을 조회합니다."""
    found = []
    search_dirs = [".", "scenarios"]
    for d in search_dirs:
        if os.path.isdir(d):
            for fname in os.listdir(d):
                if fname.endswith(".cfg"):
                    fpath = os.path.join(d, fname)
                    desc = "설명 없음"
                    with open(fpath, "r", encoding="utf-8") as f:
                        for line in f:
                            s = line.strip()
                            if s.startswith("#") and len(s) > 1:
                                desc = s.lstrip("#").strip()
                                break
                    found.append(f"- {fpath}: {desc}")
    if not found:
        return "등록된 .cfg 시나리오 파일이 없습니다."
    return "사용 가능한 목적별 복합 동작 시나리오 목록:\n" + "\n".join(found)


@mcp.tool()
def run_scenario_cfg(cfg_filename: str) -> str:
    """지정한 .cfg 시나리오 파일(예: 'greeting.cfg' 또는 'scenarios/greeting.cfg')을 읽어 목적에 맞는 복합 동작을 순차 실행합니다."""
    target_path = cfg_filename
    if not os.path.exists(target_path):
        alt_path = os.path.join("scenarios", cfg_filename)
        if os.path.exists(alt_path):
            target_path = alt_path
        else:
            return f"오류: 시나리오 파일을 찾을 수 없습니다 -> '{cfg_filename}'"

    executed_count = 0
    line_num = 0
    try:
        with open(target_path, "r", encoding="utf-8") as f:
            for line_num, raw_line in enumerate(f, start=1):
                line = raw_line.strip()
                if not line or line.startswith("#"):
                    continue

                parts = [p.strip() for p in line.split("|")]
                cmd = parts[0].lower()

                if cmd == "power" and len(parts) >= 2:
                    set_robot_power_state(parts[1])
                elif cmd == "emotion" and len(parts) >= 2:
                    play_official_move(parts[1], category="emotions")
                elif cmd == "dance" and len(parts) >= 2:
                    play_official_move(parts[1], category="dances")
                elif cmd == "move" and len(parts) >= 9:
                    z, roll, pitch, yaw, body_yaw, l_ant, r_ant, dur = map(float, parts[1:9])
                    move_head_and_body(
                        z=z, roll=roll, pitch=pitch, yaw=yaw,
                        body_yaw=body_yaw, left_antenna=l_ant, right_antenna=r_ant, duration=dur
                    )
                elif cmd == "look" and len(parts) >= 5:
                    x, y, z, dur = map(float, parts[1:5])
                    look_at_3d_point(x=x, y=y, z=z, duration=dur)
                elif cmd == "pixel" and len(parts) >= 4:
                    look_at_camera_pixel(u=int(parts[1]), v=int(parts[2]), duration=float(parts[3]))
                elif cmd == "record" and len(parts) >= 2:
                    record_motion_control(parts[1])
                elif cmd == "sleep" and len(parts) >= 2:
                    time.sleep(float(parts[1]))
                elif cmd == "reset":
                    dur = float(parts[1]) if len(parts) >= 2 else 0.8
                    reset_pose(duration=dur)
                else:
                    continue

                executed_count += 1
    except Exception as e:
        return f"실행 중 오류 발생 ({target_path} {line_num}번째 줄): {type(e).__name__} - {e}"

    return f"시나리오 '{target_path}' 복합 동작 완료 (총 {executed_count}개 스텝 실행됨)"


# ==========================================
# 4. 동작 녹화, 전원 제어 및 센서 조회
# ==========================================

@mcp.tool()
def record_motion_control(action: str) -> str:
    """로봇의 움직임 궤적을 녹화('start'), 중지('stop'), 재생('play')합니다."""
    global _recorded_trajectory
    mini = get_mini()
    if action == "start":
        mini.start_recording()
        return "모션 녹화 시작"
    elif action == "stop":
        _recorded_trajectory = mini.stop_recording()
        return "모션 녹화 중지 및 저장 완료"
    elif action == "play":
        if _recorded_trajectory is None:
            return "저장된 녹화 데이터가 없습니다."
        mini.play_move(_recorded_trajectory, initial_goto_duration=0.8)
        return "녹화된 모션 재생 완료"
    return "지원하지 않는 action입니다."


@mcp.tool()
def set_robot_power_state(state: str) -> str:
    """로봇의 기상/수면 상태 및 모터 토크 모드를 변경합니다."""
    mini = get_mini()
    if state == "wake_up":
        mini.wake_up()
    elif state == "sleep":
        mini.goto_sleep()
    elif state == "motors_on":
        mini.enable_motors()
    elif state == "motors_off":
        mini.disable_motors()
    elif state == "gravity_comp":
        mini.enable_gravity_compensation()
    return f"전원/모터 상태 '{state}' 전환 완료"


@mcp.tool()
def get_robot_joints_status() -> str:
    """현재 로봇의 모든 관절 각도를 JSON 형태로 조회합니다."""
    mini = get_mini()
    head_joints, antenna_joints = mini.get_current_joint_positions()
    return json.dumps({
        "head_joints_rad": [round(float(v), 4) for v in head_joints],
        "antennas_rad": [round(float(v), 4) for v in antenna_joints],
    }, ensure_ascii=False)


@mcp.tool()
def capture_camera_snapshot() -> str:
    """로봇 카메라에서 현재 프레임을 캡처하여 해상도 정보를 반환합니다."""
    mini = get_mini()
    frame = mini.media.get_frame()
    if frame is None:
        return "카메라 프레임을 가져올 수 없습니다."
    h, w = frame.shape[:2]
    return f"카메라 프레임 캡처 성공: 해상도 {w}x{h} 픽셀"


@mcp.resource("reachy://status/telemetry")
def telemetry_resource() -> str:
    """실시간 로봇 관절 상태 리소스"""
    return get_robot_joints_status()


if __name__ == "__main__":
    mcp.run()
