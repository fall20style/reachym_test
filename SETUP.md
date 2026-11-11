# ⚙️ Reachy Mini Simulator & MCP 환경 구축 가이드 (SETUP.md)

이 문서는 Windows 환경에서 **Reachy Mini 3D 물리 시뮬레이터(MuJoCo)**와 **MCP(Model Context Protocol) 제어 서버**, **목적별 시나리오(`.cfg`)**, **TTS 음성 출력** 환경을 처음부터 구축하는 절차를 안내합니다.

---

## 1. 시스템 요구 사항 (Prerequisites)

* **운영체제**: Windows 10 / 11 (64-bit)
* **필수 소프트웨어**:
  * **Git**: 공식 저장소 클론용
  * **Python 3.11 ~ 3.12**: `uv`가 자동으로 관리하므로 별도 설치가 없어도 무방
  * **uv**: 초고속 Python 패키지 및 가상환경 매니저
  * *(선택)* **Node.js (LTS)**: 웹 브라우저 기반 `MCP Inspector` UI 디버깅 시 필요
  * *(선택)* **Ollama**: 완전 오프라인 로컬 LLM 연동 시 필요

### `uv` 설치 (미설치 시)
PowerShell을 열고 아래 명령어를 실행하여 `uv`를 설치합니다.

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh | iex"
```
*(설치 후 새 PowerShell 창을 열거나 터미널을 재시작하여 `uv --version`이 정상 출력되는지 확인하세요.)*

---

## 2. 디렉토리 구성 및 공식 SDK 다운로드

Python 실행 시 로컬 폴더 이름(`reachy_mini`)과 설치된 패키지 이름이 충돌(`ImportError`)하는 것을 방지하기 위해 **작업 루트 폴더(`reachym_test`) 아래에 `reachy_mini` 저장소를 배치**합니다.

```powershell
# 1. 작업 루트 폴더 생성 및 이동
mkdir C:\Users\fall2\work\reachym_test
cd C:\Users\fall2\work\reachym_test

# 2. Reachy Mini 공식 SDK 저장소 클론
git clone https://github.com
```

### 완성 후 목표 폴더 구조
```text
C:\Users\fall2\work\reachym_test\
 ├── reachy_mini\                 # 공식 SDK 및 MuJoCo 가상환경 (.venv 포함)
 ├── scenarios\                   # 목적별·감정별 복합 동작 시나리오 (.cfg)
 │    ├── greeting.cfg
 │    ├── celebration.cfg
 │    └── ...
 ├── reachy_mcp_server.py         # Reachy Mini 제어용 MCP v2 서버
 ├── run_cfg_client.py            # .cfg 시나리오 인자 실행용 MCP 클라이언트
 ├── face_tracking.py             # PC 웹캠 연동 실시간 얼굴 추적 스크립트
 ├── README.md                    # 프로젝트 소개 문서
 ├── ARCHITECTURE.md              # 소프트웨어 아키텍처 문서
 └── SETUP.md                     # 환경 구축 가이드 (현재 문서)
```

---

## 3. 시뮬레이터 빌드 및 초기 실행 검증

`reachy_mini` 폴더 내부에서 `uv run --extra mujoco` 명령어를 처음 실행하면, `uv`가 자동으로 전용 가상환경(`.venv`)을 생성하고 MuJoCo 물리 엔진을 포함한 모든 필수 의존성을 빌드합니다.

```powershell
cd C:\Users\fall2\work\reachym_test\reachy_mini
uv run --extra mujoco python -m reachy_mini.daemon.app.main --sim
```

### 정상 구축 확인 포인트
1. **3D 렌더링 창**: Reachy Mini 가상 로봇이 서 있는 MuJoCo 3D 뷰어 창이 화면에 열립니다.
2. **백그라운드 데몬 서버**: 터미널에 `Uvicorn running on http://127.0.0.1:8000` 로그가 출력됩니다.
3. **웹 대시보드 접속**: 브라우저에서 `http://localhost:8000`에 접속했을 때 로봇 상태 모니터링 화면이 나타나면 시뮬레이터 환경 구축이 완료된 것입니다.

---

## 4. MCP 서버 및 시나리오 환경 설정

### ① 필수 라이브러리 구성 안내
별도의 `pip install`을 수동으로 반복할 필요 없이, `uv run` 실행 시 `--project`와 `--with` 플래그를 조합하여 격리된 상태로 즉시 실행합니다.

| 실행 목적 | 필수 추가 옵션 (`uv run` 플래그) | 비고 |
| :--- | :--- | :--- |
| **MCP 서버 & 시나리오 실행** | `--project .\reachy_mini --with mcp --with pyttsx3` | MCP v2 (`MCPServer`) + 오프라인 TTS 지원 |
| **PC 웹캠 얼굴 추적 실행** | `--project .\reachy_mini --with "opencv-python<5.0"` | OpenCV 5.0 호환성 이슈 방지를 위해 4.x 버전 고정 |

### ② 시나리오 폴더 생성 및 기본 시나리오 작성
작업 루트(`C:\Users\fall2\work\reachym_test`)에서 `scenarios` 폴더를 생성하고 테스트용 `greeting.cfg` 파일을 만듭니다.

```powershell
cd C:\Users\fall2\work\reachym_test
New-Item -ItemType Directory -Force -Path .\scenarios | Out-Null

@"
# 목적: 사용자를 발견했을 때 한국어 TTS 인사와 함께 반가워하는 복합 동작
power | wake_up
say | 안녕하세요! 반가워요. 오늘도 좋은 하루 보내세요!
emotion | cheerful1
move | 10 | 15 | -5 | 20 | 20 | 0.8 | -0.8 | 0.5
reset | 0.8
"@ | Set-Content -Encoding UTF8 .\scenarios\greeting.cfg
```

---

## 5. 통합 동작 검증 (2-터미널 테스트)

시뮬레이터 데몬과 MCP 클라이언트가 정상적으로 통신하는지 확인합니다.

### 터미널 1: 시뮬레이터 데몬 구동 (상시 유지)
```powershell
cd C:\Users\fall2\work\reachym_test\reachy_mini
uv run --extra mujoco python -m reachy_mini.daemon.app.main --sim
```

### 터미널 2: 목적별 시나리오 및 TTS 발화 테스트
```powershell
cd C:\Users\fall2\work\reachym_test
uv run --project .\reachy_mini --with mcp --with pyttsx3 python .\run_cfg_client.py greeting.cfg
```
* **예상 결과**: 터미널에 사용 가능한 시나리오 목록이 출력된 후, PC 스피커로 한국어 인사 음성이 나오며 3D 시뮬레이터 속 로봇이 반갑게 고개와 안테나를 흔듭니다.

---

## 6. LLM 호스트 연결 설정 (Claude Desktop / Cursor 등)

외부 LLM 애플리케이션에서 이 MCP 서버를 자동으로 띄워 제어하려면, 해당 앱의 MCP 설정 파일(예: Claude Desktop의 `claude_desktop_config.json`)에 아래 항목을 추가합니다.

* **Windows 설정 파일 경로**: `%APPDATA%\Claude\claude_desktop_config.json`

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
*(주의: LLM 앱에서 MCP 도구를 사용하기 전, 터미널 1의 시뮬레이터 데몬(`--sim`)이 먼저 실행되어 있어야 합니다.)*

---

## 7. 자주 발생하는 문제 해결 (Troubleshooting)

* **`ImportError: cannot import name 'ReachyMini' from 'reachy_mini'`**:
  * Python 스크립트를 클론한 `reachy_mini\` 폴더 **내부**에 두고 실행할 때 발생합니다. 반드시 바깥 폴더(`reachym_test\`)에 스크립트를 위치시키고 `--project .\reachy_mini` 옵션으로 실행하세요.
* **`warning: VIRTUAL_ENV=... will be ignored`**:
  * 다른 가상환경이 이미 활성화(`Activate.ps1`)되어 있을 때 나타나는 안내 메시지입니다. 터미널에 `deactivate`를 입력해 기존 가상환경을 해제하면 깔끔하게 사라집니다.
* **`ModuleNotFoundError: No module named 'mcp.server.fastmcp'`**:
  * MCP SDK 2.x 이상 버전에서는 `FastMCP` 대신 `from mcp.server.mcpserver import MCPServer`를 사용해야 합니다.
* **`AttributeError: module 'cv2' has no attribute 'CascadeClassifier'`**:
  * OpenCV 5.0 프리릴리즈가 설치된 경우 발생합니다. 반드시 `--with "opencv-python<5.0"` 옵션을 사용하여 4.x 안정화 버전으로 실행하세요.
