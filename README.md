# 🤖 Reachy Mini Simulator & MCP Controller

이 프로젝트는 오픈소스 데스크톱 AI 로봇 **Reachy Mini**를 실물 하드웨어 없이 **MuJoCo 3D 물리 시뮬레이터** 환경에서 구동하고, **MCP(Model Context Protocol) 서버** 및 **목적별 시나리오 파일(`.cfg`)**을 통해 LLM(로컬 Ollama, Claude Desktop 등)이 로봇의 관절·감정·춤·시선·TTS 음성을 통합 제어할 수 있도록 구축한 에이전트 제어 프레임워크입니다.

---

## ✨ 주요 기능

1. **하드웨어 추상화 및 시뮬레이션 (Sim-to-Real)**
   * 백그라운드 데몬(`reachy_mini.daemon`)과 클라이언트(`ReachyMini`)의 분리된 아키텍처를 통해, 작성된 제어 코드를 수정 없이 3D 시뮬레이터와 실물 로봇(Lite/Wireless)에 동일하게 적용할 수 있습니다.
2. **풀스펙 MCP 서버 (`reachy_mcp_server.py`)**
   * MCP Python SDK v2(`MCPServer`) 기반으로 **13개의 로봇 제어 도구(Tools)**와 **1개의 실시간 상태 리소스(Resource)**를 제공합니다.
   * 표준 출력(`stdout`) 오염 방지 처리를 적용해 JSON-RPC 통신 안정성을 확보했습니다.
3. **목적별 복합 동작 시나리오 엔진 (`.cfg`)**
   * 코드 수정 없이 텍스트 기반의 시나리오 파일(`scenarios/*.cfg`)만으로 복합 모션, 공식 감정/춤 라이브러리, 3D 시선 추적, TTS 음성 발화를 순차 실행합니다.
   * LLM이 `list_scenarios` 도구로 각 시나리오의 목적 설명을 읽고, 대화 맥락에 맞는 `.cfg` 파일을 스스로 선택해 실행할 수 있습니다.
4. **오디오 및 한국어 TTS 음성 출력**
   * 오프라인 TTS 엔진(`pyttsx3`)을 통한 즉석 텍스트 발화(`say`)와 사전 생성된 오디오 파일(`.wav` 등) 재생(`sound`)을 지원합니다.

---

## 📁 프로젝트 폴더 구조

```text
reachym_test/
 ├── reachy_mini/                 # Reachy Mini 공식 SDK 및 MuJoCo 시뮬레이터 저장소
 ├── scenarios/                   # 목적별·감정별 복합 동작 시나리오 (.cfg)
 │    ├── greeting.cfg            # 인사하며 반가워하는 복합 동작 + TTS 인사
 │    ├── celebration.cfg         # 기쁜 소식 축하 및 댄스 동작
 │    ├── listening.cfg           # 집중해서 경청 및 고개 끄덕임
 │    ├── curious_search.cfg      # 호기심 및 주변 탐색
 │    ├── surprised.cfg           # 놀람 및 당황 표현
 │    ├── sad_comfort.cfg         # 슬픔 및 위로 표현
 │    ├── thinking.cfg            # 질문에 대한 고민 및 생각 포즈
 │    ├── shy.cfg                 # 칭찬에 수줍어하는 표현
 │    ├── apology.cfg             # 사과 및 고개 숙임
 │    └── sleepy.cfg              # 피곤함 및 취침 모드 전환
 ├── reachy_mcp_server.py         # Reachy Mini 제어용 MCP v2 서버
 ├── run_cfg_client.py            # .cfg 시나리오 인자 실행용 MCP 클라이언트
 ├── face_tracking.py             # PC 웹캠 연동 실시간 얼굴 추적 스크립트
 └── README.md                    # 프로젝트 안내 문서
```

---

## 🚀 설치 및 실행 방법

모든 실행은 패키지 의존성과 가상환경 격리를 위해 **`uv`**를 사용합니다.

### 1단계: 시뮬레이터 데몬 실행 (터미널 1)
먼저 MuJoCo 3D 물리 시뮬레이터와 로컬 제어 서버(`http://127.0.0.1:8000`)를 구동합니다.

```powershell
cd C:\Users\fall2\work\reachym_test\reachy_mini
uv run --extra mujoco python -m reachy_mini.daemon.app.main --sim
```

### 2단계: 목적별 시나리오(.cfg) 실행 (터미널 2)
시뮬레이터 창이 열린 상태에서 새 터미널을 열고, 실행할 `.cfg` 파일 이름을 인자로 넘겨 복합 동작과 TTS 음성을 테스트합니다.

```powershell
cd C:\Users\fall2\work\reachym_test

# 인사 및 환영 복합 동작 실행
uv run --project .\reachy_mini --with mcp --with pyttsx3 python .\run_cfg_client.py greeting.cfg

# 축하 및 댄스 복합 동작 실행
uv run --project .\reachy_mini --with mcp --with pyttsx3 python .\run_cfg_client.py celebration.cfg
```

### 3단계: (선택) PC 웹캠 실시간 얼굴 추적 실행
```powershell
cd C:\Users\fall2\work\reachym_test
uv run --project .\reachy_mini --with "opencv-python<5.0" python .\face_tracking.py
```

---

## 🛠 MCP 서버 제공 도구 (Tools & Resources)

| 도구 / 리소스 이름 | 유형 | 설명 |
| :--- | :---: | :--- |
| `move_head_and_body` | Tool | 머리 위치(`x,y,z` mm), 회전(`roll,pitch,yaw` deg), 몸통(`body_yaw`), 안테나 정밀 제어 |
| `look_at_3d_point` | Tool | 역기구학(IK)을 이용해 3D 공간 좌표 `(x, y, z)` 응시 |
| `look_at_camera_pixel` | Tool | 카메라 영상 내 특정 픽셀 `(u, v)`가 중앙에 오도록 시선 이동 |
| `reset_pose` | Tool | 모든 관절과 안테나를 초기 정면 자세로 복귀 |
| `list_official_moves` | Tool | Hugging Face 공식 감정(86종) 및 춤(19종) 라이브러리 목록 조회 |
| `play_official_move` | Tool | 공식 감정 또는 춤 모션 실행 |
| `list_scenarios` | Tool | `scenarios/` 폴더 내 `.cfg` 시나리오 목록과 목적 설명 조회 |
| `run_scenario_cfg` | Tool | 지정한 `.cfg` 시나리오 파일의 복합 동작 및 음성 순차 실행 |
| `speak_tts` | Tool | 입력된 텍스트를 오프라인 TTS 엔진으로 즉석 발화 |
| `play_audio_file` | Tool | 미리 생성된 `.wav` / `.mp3` 오디오 파일 재생 |
| `record_motion_control` | Tool | 로봇 움직임 궤적 녹화(`start`), 저장(`stop`), 재생(`play`) |
| `set_robot_power_state` | Tool | 기상(`wake_up`), 수면(`sleep`), 모터 토크 및 중력 보상 모드 제어 |
| `get_robot_joints_status` | Tool | 현재 머리 및 안테나 관절의 실시간 라디안 각도 JSON 조회 |
| `capture_camera_snapshot` | Tool | 로봇(또는 시뮬레이터 연결) 카메라 프레임 캡처 및 해상도 확인 |
| `reachy://status/telemetry` | Resource | LLM이 직접 참조할 수 있는 실시간 관절 상태 텔레메트리 리소스 |

---

## 📝 시나리오 파일(`.cfg`) 작성 문법

`#`으로 시작하는 첫 번째 주석 줄은 `list_scenarios` 도구가 읽는 **시나리오의 목적 설명**으로 활용됩니다. 각 명령어는 파이프(`|`)로 인자를 구분합니다.

```ini
# 목적: 시나리오의 핵심 목적을 한 줄로 설명합니다 (LLM 선택 기준)

# 전원 및 기상 제어 (wake_up | sleep | motors_on | motors_off | gravity_comp)
power | wake_up

# 텍스트 즉시 TTS 음성 출력
say | 안녕하세요! 반갑습니다.

# 사전 생성된 음성 파일 재생
sound | sounds/hello.wav

# 공식 감정(86종) 또는 춤(19종) 모션 실행
emotion | cheerful1
dance | chicken_peck

# 정밀 관절 제어: move | z(mm) | roll | pitch | yaw | body_yaw | left_ant | right_ant | duration(초)
move | 12 | 15 | -5 | 20 | 20 | 0.8 | -0.8 | 0.6

# 3D 공간 좌표 응시: look | x(m) | y(m) | z(m) | duration(초)
look | 0.5 | 0.2 | 0.1 | 0.8

# 지정 시간(초) 대기 및 기본 자세 복귀
sleep | 0.5
reset | 0.8
```

---

## 🔌 LLM 클라이언트 연동 (Claude Desktop / 로컬 Ollama)

이 MCP 서버는 표준 `stdio` 프로토콜을 사용하므로 Claude Desktop이나 Cursor, 또는 로컬 Ollama 에이전트에 아래와 같이 등록하여 자연어 채팅으로 로봇을 제어할 수 있습니다.

```json
{
  "mcpServers": {
    "reachy-mini": {
      "command": "uv",
      "args": [
        "run",
        "--project",
        "C:\\Users\\fall2\\work\\reachym_test\\reachy_mini",
        "--with",
        "mcp",
        "--with",
        "pyttsx3",
        "python",
        "C:\\Users\\fall2\\work\\reachym_test\\reachy_mcp_server.py"
      ]
    }
  }
}
```


# 📂 Python 스크립트 목록 및 용도 안내 (`reachym_test`)

이 문서는 `C:\Users\fall2\work\reachym_test` 디렉터리에 작성된 Python 스크립트(`*.py`)들의 핵심 역할과 분류를 정리한 목록입니다.

---

## 1. 핵심 운영 스크립트 (Core Scripts)

| 파일명 | 크기 | 주요 용도 및 역할 |
| :--- | :---: | :--- |
| **`reachy_mcp_server.py`** | 10,991 B | **메인 MCP v2 서버**: LLM 호스트(Claude Desktop, Cursor, Ollama 등)가 로봇의 관절, 감정, 춤, 3D 시선 추적, TTS 및 녹음 음성을 제어할 수 있도록 14개의 도구(Tools)와 1개의 리소스를 제공합니다. |
| **`run_cfg_client.py`** | 1,140 B | **시나리오(`.cfg`) 실행 클라이언트**: 커맨드라인 인자로 특정 `.cfg` 파일 또는 디렉터리(`scenarios`)와 반복 옵션(`--loop`)을 받아 MCP 서버에 복합 동작 실행을 요청합니다. |
| **`llm_controller.py`** | 5,055 B | **로컬 LLM 직접 연동 에이전트**: 로컬 Ollama LLM과 통신하여 생성된 한국어 답변과 감정 태그에 맞춰 로봇의 고개와 안테나 움직임을 제어합니다. |
| **`face_tracking.py`** | 3,012 B | **실시간 웹캠 얼굴 추적**: PC 웹캠(`OpenCV`)으로 사용자 얼굴 좌표를 실시간 인식하여 시뮬레이터 속 가상 로봇이 시선을 따라 움직이도록 비동기(`set_target`) 제어합니다. |

---

## 2. 기능 검증 및 테스트 스크립트 (Test & Utility Scripts)

| 파일명 | 크기 | 주요 용도 및 역할 |
| :--- | :---: | :--- |
| **`test_mcp_client_all.py`** | 4,150 B | **MCP 통합 기능 데모 클라이언트**: 감정 표현, 공식 춤 동작, 정밀 관절 제어, 3D 시선 추적 도구를 연속 시나리오로 실행하여 MCP 서버 전체 기능을 검증합니다. |
| **`test_mcp_client.py`** | 2,109 B | **MCP 기본 연결 테스트 클라이언트**: MCP 서버 초기화, 등록된 도구 목록 조회(`list_tools`), 단일 모션(`cheerful1`) 호출이 정상 작동하는지 확인합니다. |
| **`emotion.py`** | 264 B | **단일 공식 모션 SDK 테스트**: MCP를 거치지 않고 `ReachyMini` SDK의 `RecordedMoves`를 직접 호출해 특정 감정 모션 재생 여부를 확인하는 초기 테스트 코드입니다. |
| **`emotion_list.py`** | 208 B | **공식 라이브러리 목록 조회 유틸리티**: Hugging Face에 호스팅된 공식 감정(86종) 및 춤(19종) 데이터셋의 정확한 이름 목록을 터미널에 출력합니다. |
