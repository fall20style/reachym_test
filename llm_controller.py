# llm_controller.py

import os
import json
import time
import numpy as np
from openai import OpenAI
from reachy_mini import ReachyMini
from reachy_mini.utils import create_head_pose


exaone_key = os.getenv("EXAONE_API_KEY")
if not exaone_key:
    raise ValueError("EXAONE_API_KEY 환경변수가 비어 있습니다.")

client = OpenAI(
    base_url="https://api.exaone.ai/v1",
    api_key=exaone_key,
)

MODEL_NAME = "k-exaone_v2.5"  # OpenAI 사용 시 "gpt-4o-mini" 등으로 변경

# 2. LLM에게 로봇 제어 규칙과 JSON 출력 형식을 알려주는 시스템 프롬프트
SYSTEM_PROMPT = """
당신은 소형 휴머노이드 로봇 'Reachy Mini'의 제어 브레인입니다.
사용자의 자연어 입력을 분석하여 로봇이 취해야 할 물리적 동작과 짧은 대답을 반드시 아래 JSON 형식으로만 출력하세요.

[가능한 action 종류와 params 규격]
1. "nod": 고개 끄덕이기 (긍정, 동의) -> {"times": 1~3 정수}
2. "shake": 고개 좌우로 젓기 (부정, 거절) -> {"times": 1~3 정수}
3. "tilt": 고개 갸웃거리기 (호기심, 의문) -> {"angle": -25~25 각도}
4. "look": 특정 방향 바라보기 -> {"yaw": -45~45(좌우), "pitch": -30~30(상하)}
5. "antennas": 양쪽 안테나 움직이기 -> {"left": -45~45, "right": -45~45}
6. "reset": 정면 기본 자세로 복귀 -> {}

[출력 JSON 예시]
{
  "reply": "네, 알겠습니다!",
  "actions": [
    {"action": "antennas", "params": {"left": 30, "right": 30}},
    {"action": "nod", "params": {"times": 2}}
  ]
}
"""

# 3. 실제 Reachy Mini 하드웨어(또는 시뮬레이터) 동작 실행 함수
def execute_robot_actions(mini: ReachyMini, actions: list):
    for item in actions:
        act = item.get("action")
        p = item.get("params", {})

        if act == "nod":
            times = int(p.get("times", 2))
            for _ in range(times):
                mini.goto_target(head=create_head_pose(pitch=15, degrees=True), duration=0.35)
                mini.goto_target(head=create_head_pose(pitch=-10, degrees=True), duration=0.35)
            mini.goto_target(head=create_head_pose(), duration=0.4)

        elif act == "shake":
            times = int(p.get("times", 2))
            for _ in range(times):
                mini.goto_target(head=create_head_pose(yaw=20, degrees=True), duration=0.35)
                mini.goto_target(head=create_head_pose(yaw=-20, degrees=True), duration=0.35)
            mini.goto_target(head=create_head_pose(), duration=0.4)

        elif act == "tilt":
            angle = float(p.get("angle", 20))
            mini.goto_target(head=create_head_pose(roll=angle, degrees=True), duration=0.6)

        elif act == "look":
            yaw = float(p.get("yaw", 0))
            pitch = float(p.get("pitch", 0))
            mini.goto_target(head=create_head_pose(yaw=yaw, pitch=pitch, degrees=True), duration=0.7)

        elif act == "antennas":
            left_rad = np.deg2rad(float(p.get("left", 0)))
            right_rad = np.deg2rad(float(p.get("right", 0)))
            mini.goto_target(antennas=[right_rad, left_rad], duration=0.5)

        elif act == "reset":
            mini.goto_target(head=create_head_pose(), antennas=[0.0, 0.0], duration=0.7)

        time.sleep(0.2)

# 4. 자연어를 받아 LLM 호출 및 파싱
def process_natural_language(user_text: str) -> dict:
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_text}
        ],
        temperature=0.2,
    )
    raw_content = response.choices[0].message.content.strip()

    # 마크다운 코드블록(```json ... ```)이 포함된 경우 제거
    if "```" in raw_content:
        raw_content = raw_content.split("```")[1]
        if raw_content.startswith("json"):
            raw_content = raw_content[4:]

    return json.loads(raw_content.strip())

# 5. 메인 실행 루프
def main():
    print("Reachy Mini 연결 중...")
    with ReachyMini() as mini:
        # 시작 시 기본 자세 정렬
        mini.goto_target(head=create_head_pose(), antennas=[0.0, 0.0], duration=1.0)
        print("연결 완료! 자연어로 명령을 입력해 보세요. (종료: exit)\n")

        while True:
            user_input = input("나: ").strip()
            if not user_input:
                continue
            if user_input.lower() in ["exit", "quit", "종료"]:
                break

            try:
                result = process_natural_language(user_input)
                print(f"Reachy: {result.get('reply', '')}")
                print(f"[실행 동작]: {result.get('actions', [])}\n")
                execute_robot_actions(mini, result.get("actions", []))
            except Exception as e:
                print(f"처리 중 오류가 발생했습니다: {e}\n")

if __name__ == "__main__":
    main()
