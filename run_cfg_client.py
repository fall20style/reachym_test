import asyncio
import os
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():
    if len(sys.argv) < 2:
        print("사용법: uv run --project .\\reachy_mini --with mcp python .\\run_cfg_client.py <시나리오파일.cfg>")
        return

    cfg_filename = sys.argv[1]
    server_script = os.path.abspath("reachy_mcp_server.py")
    server_params = StdioServerParameters(command=sys.executable, args=[server_script])

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            list_res = await session.call_tool("list_scenarios", arguments={})
            print(list_res.content[0].text + "\n")

            print(f"'{cfg_filename}' 복합 동작 실행 요청 중...")
            run_res = await session.call_tool(
                "run_scenario_cfg", arguments={"cfg_filename": cfg_filename}
            )
            print("결과 ->", run_res.content[0].text)


if __name__ == "__main__":
    asyncio.run(main())
