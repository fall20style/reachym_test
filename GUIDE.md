# 🤖 Reachy Mini Simulator & MCP AI Agent 통합 가이드

이 문서는 오픈소스 데스크톱 AI 로봇 **Reachy Mini**의 공식 SDK를 `git clone`으로 내려받아 **MuJoCo 3D 물리 시뮬레이터** 환경을 구축하고, **MCP(Model Context Protocol) v2 서버**, **목적별 시나리오(`.cfg`)**, **로컬 LLM(Ollama) 및 TTS·녹음 음성 출력**까지 연동하는 전체 지식과 실행 가이드를 하나로 통합한 레퍼런스입니다.

---

## 1. Reachy Mini 개요 및 아키텍처 이해

* **하드웨어 & 특징**: Hugging Face와 Pollen Robotics가 공동 개발한 오픈소스(Apache 2.0) 데스크톱 교감 로봇입니다. 6자유도(6-DOF) 스튜어트 플랫폼 머리, 1축 몸통 회전, 2축 안테나(총 9-DOF)와 12MP 광각 카메라, 4마이크 배열을 갖추고 있습니다.
* **클라이언트-서버 구조 (Sim-to-Real)**:
  * **백그라운드 데몬 (`reachy_mini.daemon`)**: 포트 `8000`(REST API / WebSocket)에서 실행되며 역기구학(IK) 계산, 관절 안전 각도 제한, 물리 엔진 구동을 담당합니다.
  * **클라이언트 (`ReachyMini` 객체)**: 데몬에 명령을 보내는 얇은(Thin) 인터페이스입니다. 코드 수정 없이 **3D 시뮬레이터(`--sim`)**, **유선 기기(Lite)**, **무선 기기(Wireless)**에 100% 동일하게 작동합니다.
* **시뮬레이터(`--sim`) vs 실물 기기 차이**:
  * 9축 관절 움직임과 SDK API는 100% 동일합니다.
  * 카메라는 PC 기본 웹캠으로, 마이크·스피커는 PC 기본 오디오 장치로 대체되며, 가속도계(IMU)와 배터리 상태는 시뮬레이션되지 않습니다.

---

## 2. 디렉토리 구조 및 초기 설치 (`git clone` + `uv`)

### ① 권장 폴더 구조
Python 실행 시 로컬 저장소 폴더 이름(`reachy_mini`)과 설치된 패키지 이름이 충돌(`ImportError`)하는 것을 막기 위해 **상위 작업 폴더(`reachym_test`) 아래에 저장소를 클론**하고, 사용자 스크립트는 바깥에 배치합니다.

```text
C:\Users\fall2\work\reachym_test\
 ├── reachy_mini\                 # git clone으로 받은 공식 SDK 및 가상환경(.venv)
 ├── scenarios\                   # 목적별·감정별 복합 동작 시나리오 (.cfg)
 │    ├── greeting.cfg
 │    └── celebration.cfg
 ├── sounds\                      # 사용자 녹음 음성 파일 (.wav / .mp3)
 │    └── hello_owner.wav
 ├── reachy_mcp_server.py         # Reachy Mini 제어용 MCP v2 서버
 ├── run_cfg_client.py            # .cfg 시나리오 인자 실행용 MCP 클라이언트
 ├── face_tracking.py             # PC 웹캠 실시간 얼굴 추적 스크립트
 └── GUIDE.md                     # 통합 가이드 문서
```

### ② `uv` 설치 및 저장소 클론
```powershell
# 1. uv 패키지 매니저 설치 (미설치 시)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh | iex"

# 2. 작업 폴더 생성 및 공식 저장소 클론
mkdir C:\Users\fall2\work\reachym_test
cd C:\Users\fall2\work\reachym_test
git clone https://github.com
```

### ③ 시뮬레이터 최초 빌드 및 실행 (터미널 1)
저장소 폴더(`reachy_mini`) 내부에서 `--extra mujoco` 옵션으로 실행하면 `uv`가 자동으로 `.venv` 가상환경을 만들고 3D 시뮬레이터를 빌드·실행합니다.

```powershell
cd C:\Users\fall2\work\reachym_test\reachy_mini
uv run --extra mujoco python -m reachy_mini.daemon.app.main --sim
```
* **정상 확인**: MuJoCo 3D 뷰어 창이 열리고 `http://127.0.0.1:8000` 웹 대시보드 접속이 가능합니다.

---

## 3. 핵심 제어 API 및 실전 예제

### ① 모션 제어 3대 메서드 (`ReachyMini` 객체)
* **`goto_target(head, antennas, body_yaw, duration)`**: 지정된 시간 동안 부드럽게 보간 이동하는 **동기(Blocking)** 명령입니다. 순차적인 감정 표현에 사용합니다.
* **`set_target(head, antennas)`**: 대기 시간 없이 목표 좌표를 즉시 덮어쓰는 **비동기(Non-blocking)** 명령입니다. 웹캠 얼굴 추적처럼 초당 30프레임 갱신 루프에 사용합니다.
* **`look_at_world(x, y, z)` / `look_at_image(u, v)`**: 역기구학(IK)을 자동 계산해 3D 공간 좌표(m) 또는 이미지 픽셀 좌표를 응시합니다.

### ② PC 웹캠 얼굴 추적 실행 (`face_tracking.py`)
```powershell
cd C:\Users\fall2\work\reachym_test
uv run --project .\reachy_mini --with "opencv-python<5.0" python .\face_tracking.py
```

---

## 4. MCP(Model Context Protocol) v2 서버 구축

LLM(Claude Desktop, Cursor, 로컬 Ollama)이 로봇을 제어할 수 있도록 MCP Python SDK v2(`MCPServer`) 기반의 미들웨어 서버를 구축했습니다.

### ① MCP 서버 핵심 설계 원칙
* **`stdout` 오염 방지**: MCP `stdio` 통신은 표준 출력(`stdout`)을 JSON-RPC 전용으로 사용하므로, `ReachyMini()` 및 `RecordedMoves()` 호출 시 반드시 **`contextlib.redirect_stdout(sys.stderr)`**로 감싸 로그를 `stderr`로 우회합니다.
* **지연 초기화 (Lazy Init)**: 서버 부팅 타임아웃을 막기 위해 실제 도구가 처음 호출될 때 `get_mini()`로 로봇 데몬에 연결합니다.

### ② 제공 도구 (Tools) 및 리소스 (Resource)
* **정밀 제어**: `move_head_and_body`, `look_at_3d_point`, `look_at_camera_pixel`, `reset_pose`
* **공식 모션 라이브러리**: `list_official_moves` (감정 86종 / 춤 19종 조회), `play_official_move` (예: `cheerful1`, `amazed1`, `chicken_peck`)
* **시나리오 엔진**: `list_scenarios` (`.cfg` 목록 및 주석 설명 조회), `run_scenario_cfg` (복합 동작 순차 실행)
* **음성 및 오디오**: `speak_tts` (오프라인 TTS 즉시 발화), `play_recorded_voice` (녹음된 `.wav`/`.mp3` 동기·비동기 재생)
* **녹화·전원·센서**: `record_motion_control` (`start`/`stop`/`play`), `set_robot_power_state` (`wake_up`/`sleep`/`gravity_comp`), `get_robot_joints_status`, `capture_camera_snapshot`, `reachy://status/telemetry` (Resource)

---

## 5. 목적별 시나리오(`.cfg`) 및 음성 연동

코드 수정 없이 텍스트 파일(`scenarios/*.cfg`) 한 줄씩 명령을 적어 복합 동작과 음성을 조합할 수 있습니다.

### ① `.cfg` 작성 문법 예시 (`scenarios/greeting.cfg`)
```ini
# 목적: 사용자를 발견했을 때 녹음된 내 목소리와 함께 반가워하는 복합 동작
power | wake_up

# 녹음된 목소리 비동기 재생 (음성이 나오는 동안 아래 동작 동시 실행)
voice | sounds/hello_owner.wav | async

# 또는 즉석 한국어 TTS 발화
# say | 안녕하세요! 반가워요!

# 고개 끄덕임 및 공식 감정/춤 실행
move | 12 | 0 | 20 | 0 | 0 | 0.8 | -0.8 | 0.45
emotion | cheerful1
dance | groovy_sway_and_roll
sleep | 0.5
reset | 0.8
```

### ② 시나리오 실행 명령어 (터미널 2)
```powershell
cd C:\Users\fall2\work\reachym_test
uv run --project .\reachy_mini --with mcp --with pyttsx3 --with pygame python .\run_cfg_client.py greeting.cfg
```

---

## 6. LLM 연동 (Claude Desktop & 로컬 Ollama)

### ① Claude Desktop / Cursor MCP 등록 (`claude_desktop_config.json`)
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
        "--with",
        "pygame",
        "python",
        "C:\\Users\\fall2\\work\\reachym_test\\reachy_mcp_server.py"
      ]
    }
  }
}
```

### ② 노트북 로컬 LLM (Ollama) 연동
노트북에서 `ollama pull qwen2.5:7b` 실행 후 `http://localhost:11434/api/chat` 엔드포인트에 JSON 포맷 응답(`{"reply": "...", "emotion": "..."}`)을 요청하면 외부 인터넷 없이 완전한 온디바이스 AI 로봇처럼 구동할 수 있습니다.

---

## 7. 핵심 트러블슈팅 요약 (FAQ)

| 발생한 문제 | 원인 | 해결 방법 |
| :--- | :--- | :--- |
| `mjpython` 인식 불가 | macOS 전용 실행기임 | Windows에서는 일반 `python`으로 실행 |
| `MuJoCo is not installed` | 기본 설치 시 물리 엔진 제외됨 | `uv run --extra mujoco ...` 옵션 추가 |
| `ImportError: cannot import name 'ReachyMini'` | 스크립트가 `reachy_mini/` 폴더 안에 있음 | 바깥 폴더(`reachym_test/`)로 이동 후 `--project .\reachy_mini` 사용 |
| `VIRTUAL_ENV=... will be ignored` 경고 | 기존 가상환경이 활성화되어 충돌함 | 터미널에 `deactivate` 입력 후 실행 |
| `cv2`에 `CascadeClassifier` 없음 | OpenCV 5.0 프리릴리즈 호환성 문제 | `--with "opencv-python<5.0"`으로 4.x 버전 지정 |
| `No module named 'mcp.server.fastmcp'` | MCP SDK 2.x에서 클래스명 변경 | `from mcp.server.mcpserver import MCPServer` 사용 |
| `MCPError: Connection closed` | `stdout` 로그 오염 또는 `uv` 중첩 호출 | 서버는 `redirect_stdout(sys.stderr)` 적용, 클라이언트는 `sys.executable` 직접 호출 |
| `AttributeError: 'list' object has no attribute 'text'` | MCP 응답의 `.content`가 리스트 타입임 | `res.content.text`처럼 인덱스 `` 명시 |
| `'happy'` 모션 실행 실패 | 공식 라이브러리는 뒤에 번호가 붙음 | `list_official_moves`로 확인 후 `'cheerful1'` 등 정확한 이름 사용 |
