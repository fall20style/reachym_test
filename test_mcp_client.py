import asyncio
import os
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():
    # 현재 가상환경의 python.exe 경로와 서버 스크립트의 절대 경로를 직접 지정
    server_script = os.path.abspath("reachy_mcp_server.py")
    server_params = StdioServerParameters(
        command=sys.executable,
        args=[server_script],
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # 1. 등록된 전체 MCP 도구 목록 조회
            tools = await session.list_tools()
            print(f"총 {len(tools.tools)}개의 MCP 도구 등록됨:")
            for t in tools.tools:
                first_line = t.description.splitlines()[0] if t.description else ""
                print(f" - {t.name}: {first_line}")

            # 2. 현재 로봇 관절 상태 조회
            status = await session.call_tool("get_robot_joints_status", arguments={})
            print("\n현재 관절 상태:", status.content[0].text)

            # 3. 공식 모션 라이브러리(감정) 목록 조회
            moves = await session.call_tool(
                "list_official_moves", arguments={"category": "emotions"}
            )
            print("\n" + moves.content[0].text[:150] + "...")

            # 4. 실제 존재하는 공식 감정 모션('cheerful1') 실행
            print("\n'cheerful1' 공식 감정 모션을 실행합니다...")
            res = await session.call_tool(
                "play_official_move",
                arguments={"move_name": "cheerful1", "category": "emotions"},
            )
            print("모션 실행 결과:", res.content[0].text)

            # 5. 기본 정면 자세로 복귀
            reset_res = await session.call_tool("reset_pose", arguments={"duration": 0.8})
            print("복귀 결과:", reset_res.content[0].text)


if __name__ == "__main__":
    asyncio.run(main())
