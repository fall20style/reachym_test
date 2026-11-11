# 🏗 Reachy Mini MCP Agent — 소프트웨어 아키텍처 (ARCHITECTURE.md)

이 문서는 **Reachy Mini 3D 시뮬레이터(MuJoCo)**를 기반으로 LLM(로컬 Ollama, Claude Desktop 등)이 로봇의 관절, 감정 모션, 시선 추적, TTS 음성을 통합 제어하기 위해 구축한 **계층형 클라이언트-서버 아키텍처**를 설명합니다.

---

## 1. 전체 시스템 토폴로지 (System Topology)

본 시스템은 **AI 추론 계층(LLM Host) ➔ 도구 중계 계층(MCP Server) ➔ 로봇 추상화 계층(SDK Client) ➔ 하드웨어/물리 실행 계층(Daemon & MuJoCo)**의 4단계 파이프라인으로 분리되어 있습니다.

```text
+-----------------------------------------------------------------------+

|  1. AI 추론 / 클라이언트 계층 (LLM Host 또는 CLI 테스트 클라이언트)   |
|     - Claude Desktop / Cursor / 로컬 Ollama 에이전트 / run_cfg_client |
+-----------------------------------+-----------------------------------+
                                    |  MCP Protocol (JSON-RPC over stdio)
                                    ▼
+-----------------------------------------------------------------------+

|  2. MCP 미들웨어 및 시나리오 엔진 (reachy_mcp_server.py)              |
|     - FastMCP / MCPServer v2 인터페이스 (14 Tools + 1 Resource)       |
|     - .cfg 시나리오 인터프리터 (scenarios/*.cfg 순차 파싱 및 실행)     |
|     - 오프라인 TTS 엔진(pyttsx3) 및 오디오 폴백 제어                  |
|     - stdout 보호 래퍼 (contextlib.redirect_stdout -> stderr)         |
+-----------------------------------+-----------------------------------+
                                    |  Python SDK Calls (ReachyMini 객체)
                                    ▼
+-----------------------------------------------------------------------+

|  3. 로봇 제어 백그라운드 데몬 (reachy_mini.daemon - Port 8000)         |
|     - REST API / WebSocket 서버 (127.0.0.1:8000)                      |
|     - 역기구학(IK) 솔버 & 스튜어트 플랫폼(6-DOF) 궤적 보간기          |
|     - 관절 안전 각도 제한(Safety Limits) 및 충돌 검증                 |
+-----------------------------------+-----------------------------------+
                                    |  Internal Physics / Hardware Bus
                                    ▼
+-----------------------------------------------------------------------+

|  4. 물리 시뮬레이션 / 하드웨어 계층 (Sim-to-Real Abstraction)         |
|     - [현재] MuJoCo 3D 물리 엔진 (--sim) + PC 웹캠/스피커             |
|     - [확장] Reachy Mini 실물 기기 (Lite USB / Wireless RPi CM4)      |
+-----------------------------------------------------------------------+
```

---

## 2. 계층별 핵심 설계 및 역할

### ① AI 추론 및 클라이언트 계층 (Client Layer)
* **역할**: 사용자의 자연어 의도를 파악하거나 미리 정의된 테스트 명령을 전달합니다.
* **구성 요소**:
  * **LLM Host (Claude Desktop, Cursor, Ollama)**: `list_scenarios`와 `list_official_moves`를 통해 로봇이 수행할 수 있는 행동 목록을 탐색한 뒤, 대화 맥락에 맞는 도구(`run_scenario_cfg`, `move_head_and_body`, `speak_tts` 등)를 호출합니다.
  * **CLI 시나리오 러너 (`run_cfg_client.py`)**: LLM 개입 없이 커맨드라인 인자(`greeting.cfg` 등)만으로 MCP 서버의 기능을 검증하는 경량 테스트 클라이언트입니다.

### ② MCP 미들웨어 및 시나리오 엔진 (`reachy_mcp_server.py`)
* **프로토콜 격리 (`stdout` 보호)**:
  * MCP 표준 `stdio` 전송 방식은 표준 출력(`stdout`)을 JSON-RPC 메시지 전용 파이프로 사용합니다.
  * `ReachyMini()` 초기화나 Hugging Face 데이터셋 다운로드 시 발생하는 일반 로그가 `stdout`을 오염시켜 통신이 끊어지는 현상을 막기 위해 **`contextlib.redirect_stdout(sys.stderr)`**를 적용했습니다.
* **지연 초기화 (Lazy Initialization)**:
  * MCP 서버 프로세스 부팅 시점에 즉시 로봇 데몬에 접속하지 않고, 실제 로봇 제어 도구가 처음 호출될 때 `get_mini()`를 통해 싱글톤(`_mini`) 연결을 생성하여 서버 시작 타임아웃을 방지합니다.
* **목적별 시나리오 인터프리터 (`run_scenario_cfg`)**:
  * 파이프(`|`) 구분자로 작성된 `.cfg` 파일을 한 줄씩 파싱하여 복합 동작(기상 ➔ TTS 인사 ➔ 감정 모션 ➔ 시선 이동 ➔ 원위치 복귀)을 단일 MCP 도구 호출로 압축 실행합니다.

### ③ 로봇 제어 데몬 (`reachy_mini.daemon`)
* **클라이언트-서버 분리**:
  * `ReachyMini` 객체는 얇은(Thin) 클라이언트이며, 실제 연산은 백그라운드 데몬(`localhost:8000`)이 담당합니다.
  * 덕분에 웹 대시보드(`http://localhost:8000`)와 MCP 서버, 별도의 얼굴 추적 스크립트(`face_tracking.py`)가 동시에 데몬 상태를 조회하거나 명령을 보낼 수 있습니다.
* **모션 제어 방식의 이원화**:
  * **동기식 궤적 제어 (`goto_target`)**: MCP 도구처럼 순차적인 동작 완료가 보장되어야 할 때 사용합니다(`minjerk`, `cartoon` 등의 보간 알고리즘 지원).
  * **비동기 실시간 제어 (`set_target`)**: `face_tracking.py`처럼 초당 30프레임으로 웹캠 좌표를 추적하며 목표 각도를 즉시 덮어쓸 때 사용합니다.

### ④ 물리 시뮬레이션 및 Sim-to-Real 계층
* **MuJoCo 물리 엔진**: 6축 스튜어트 플랫폼(머리), 1축 베이스 회전(몸통), 2축 안테나의 역기구학 및 물리적 관성을 실시간 렌더링합니다.
* **무수정 하드웨어 전환**: MCP 서버는 오직 `localhost:8000` 표준 인터페이스만 바라보므로, 추후 시뮬레이터 데몬 대신 실물 Reachy Mini 기기(Lite 또는 Wireless)의 데몬에 연결해도 MCP 서버와 `.cfg` 시나리오 코드를 수정할 필요가 없습니다.

---

## 3. 주요 실행 흐름 (Sequence Diagram)

LLM 또는 CLI 클라이언트가 `greeting.cfg` 복합 동작을 요청할 때의 내부 데이터 흐름입니다.

```text
Client (LLM/CLI)          MCP Server (reachy_mcp_server)        Reachy Daemon (MuJoCo)

      |                                 |                                  |
      |--- call_tool("list_scenarios") ->|                                  |
      |<-- scenarios/greeting.cfg 목록 --|                                  |
      |                                 |                                  |
      |--- call_tool("run_scenario_cfg", "greeting.cfg") ----------------->|
      |                                 |--- [1] get_mini() 연결 생성 ----->|
      |                                 |<-- REST/WS 세션 확립 (Port 8000) -|
      |                                 |                                  |
      |                                 |--- [2] power | wake_up ---------->|
      |                                 |--- [3] say | "안녕하세요!" (TTS)  | (PC 스피커 출력)
      |                                 |--- [4] emotion | cheerful1 ------>| (3D 모션 렌더링)
      |                                 |--- [5] reset | 0.8 -------------->| (정면 자세 복귀)
      |                                 |                                  |
      |<-- "시나리오 복합 동작 완료" -----|                                  |
```

---

## 4. 확장 포인트 (Extensibility)

1. **멀티모달 비전(VLM) 확장**: `capture_camera_snapshot` 도구의 반환 타입을 텍스트 요약에서 MCP 표준 `ImageContent`(Base64 JPEG)로 확장하면, 비전 지원 LLM이 로봇 시야를 직접 보고 상황을 판단할 수 있습니다.
2. **비동기 발화-동작 동기화**: 현재 `speak_tts`는 발화가 끝날 때까지 대기한 후 다음 동작을 수행하지만, `threading` 또는 `asyncio` 태스크로 분리하면 로봇이 말을 하는 동안 동시에 고개와 안테나를 움직이는 자연스러운 제스처를 구현할 수 있습니다.
3. **영구 커스텀 모션 저장**: `record_motion_control`로 메모리에 녹화한 관절 궤적(`Move` 객체)을 JSON 파일로 직렬화하여 `scenarios/` 폴더와 연계하면, 사용자가 손으로 가르친 움직임을 시나리오의 일부로 영구 재사용할 수 있습니다.
