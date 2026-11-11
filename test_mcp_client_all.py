import asyncio
import os
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():
    server_script = os.path.abspath("reachy_mcp_server.py")
    server_params = StdioServerParameters(
        command=sys.executable,
        args=[server_script],
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # 1. 사용 가능한 전체 감정 및 춤 목록 먼저 확인
            emotions_res = await session.call_tool(
                "list_official_moves", arguments={"category": "emotions"}
            )
            dances_res = await session.call_tool(
                "list_official_moves", arguments={"category": "dances"}
            )
            print("=== 공식 라이브러리 목록 ===")
            print(emotions_res.content[0].text)
            print(dances_res.content[0].text)
            print("=" * 40)

            # 2. 공식 감정 모션 연속 재생 (놀람 -> 호기심 -> 신남)
            demo_emotions = ["amazed1", "attentive1", "cheerful1"]
            for emo in demo_emotions:
                print(f"\n[감정 표현 실행] '{emo}' 재생 중...")
                res = await session.call_tool(
                    "play_official_move",
                    arguments={"move_name": emo, "category": "emotions"},
                )
                print(" ->", res.content[0].text)
                await asyncio.sleep(0.5)

            # 3. 정밀 관절 제어 (고개 갸우뚱 + 몸통 회전 + 안테나 흔들기)
            print("\n[정밀 관절 제어] 고개를 갸우뚱하며 몸통을 돌립니다...")
            move_res = await session.call_tool(
                "move_head_and_body",
                arguments={
                    "z": 15.0,
                    "roll": 25.0,
                    "pitch": -10.0,
                    "yaw": 20.0,
                    "body_yaw": 35.0,
                    "left_antenna": 0.8,
                    "right_antenna": -0.8,
                    "duration": 1.2,
                    "method": "cartoon",
                },
            )
            print(" ->", move_res.content[0].text)
            await asyncio.sleep(0.5)

            # 4. 3D 공간 좌표 응시 (허공의 왼쪽 위 -> 오른쪽 아래 바라보기)
            print("\n[3D 시선 추적] 왼쪽 위 좌표를 응시합니다...")
            await session.call_tool(
                "look_at_3d_point", arguments={"x": 0.5, "y": 0.3, "z": 0.25, "duration": 0.8}
            )
            await asyncio.sleep(0.4)

            print("[3D 시선 추적] 오른쪽 아래 좌표를 응시합니다...")
            await session.call_tool(
                "look_at_3d_point", arguments={"x": 0.5, "y": -0.3, "z": -0.1, "duration": 0.8}
            )
            await asyncio.sleep(0.5)

            # 5. 공식 춤(Dances) 라이브러리 중 첫 번째 춤 실행
            raw_dance_text = dances_res.content[0].text
            if "[" in raw_dance_text and "]" in raw_dance_text:
                dance_list_str = raw_dance_text.split("[")[-1].split("]")[0]
                first_dance = dance_list_str.split(",")[0].strip().strip("'\"")
                if first_dance:
                    print(f"\n[공식 춤 재생] '{first_dance}' 댄스 실행 중...")
                    dance_res = await session.call_tool(
                        "play_official_move",
                        arguments={"move_name": first_dance, "category": "dances"},
                    )
                    print(" ->", dance_res.content[0].text)
                    await asyncio.sleep(0.5)

            # 6. 기본 정면 자세로 복귀
            print("\n[마무리] 기본 자세로 복귀합니다...")
            reset_res = await session.call_tool("reset_pose", arguments={"duration": 1.0})
            print(" ->", reset_res.content[0].text)


if __name__ == "__main__":
    asyncio.run(main())
