# 🛠️ Reachy Mini Simulator & MCP 트러블슈팅 기록 (TROUBLESHOOTS.md)

이 문서는 Windows 환경에서 **Reachy Mini MuJoCo 시뮬레이터**, **`uv` 패키지 매니저**, **OpenCV 얼굴 추적**, 그리고 **MCP(Model Context Protocol) v2 서버**를 구축하면서 실제로 겪었던 주요 오류들의 원인과 해결 방법을 정리한 기록입니다.

---

## 1. 시뮬레이터 실행 및 환경 설정 이슈

### 1-1. `mjpython` 명령어 인식 불가 (Windows 환경)
* **에러 메시지**:
  ```text
  mjpython : 'mjpython' 용어가 cmdlet, 함수, 스크립트 파일 또는 실행할 수 있는 프로그램 이름으로 인식되지 않습니다.
  ```
* **원인**: `mjpython`은 macOS에서 GUI 메인 스레드 제약 때문에 사용하는 전용 실행기이며, Windows 환경에서는 존재하지 않습니다.
* **해결 방법**: Windows에서는 일반 `python` 명령어(또는 `uv run`을 통한 `python`)로 데몬을 실행합니다.
  ```powershell
  uv run --extra mujoco python -m reachy_mini.daemon.app.main --sim
  ```

### 1-2. `MuJoCo is not installed` 데몬 시작 실패
* **에러 메시지**:
  ```text
  Failed to start daemon: MuJoCo is not installed. MuJoCo backend is not available.
  ```
* **원인**: `uv run`으로 기본 패키지만 설치할 경우 선택적 의존성(Extra)인 `mujoco` 물리 엔진이 포함되지 않습니다.
* **해결 방법**: 실행 시 반드시 `--extra mujoco` 플래그를 명시하여 실행합니다.
  ```powershell
  uv run --extra mujoco python -m reachy_mini.daemon.app.main --sim
  ```

### 1-3. `warning: VIRTUAL_ENV=... will be ignored` 경고 메시지
* **경고 메시지**:
  ```text
  warning: `VIRTUAL_ENV=C:\Users\fall2\work\reachy_mini\.venv` does not match the project environment path `reachy_mini\.venv` and will be ignored; use `--active` to target the active environment instead
  ```
* **원인**: 터미널에 이전 경로의 가상환경(`Activate.ps1`)이 이미 활성화된 상태에서 `uv run --project`를 실행하여, `uv`가 기존 활성 환경을 무시하고 프로젝트 전용 `.venv`를 우선 선택했기 때문입니다.
* **해결 방법**: 터미널에서 `deactivate`를 입력해 기존 가상환경 활성화를 해제하거나 새 PowerShell 창을 열어 실행합니다.

---

## 2. 패키지 임포트 및 의존성 충돌 이슈

### 2-1. `ImportError: cannot import name 'ReachyMini' from 'reachy_mini' (unknown location)`
* **에러 메시지**:
  ```text
  ImportError: cannot import name 'ReachyMini' from 'reachy_mini' (unknown location)
  ```
* **원인**: 실행하려는 Python 스크립트(`face_tracking.py` 등)가 클론받은 `reachy_mini/` 저장소 폴더 **내부**에 위치해 있어, Python이 설치된 라이브러리가 아닌 로컬 디렉토리 이름을 패키지로 착각해 먼저 불러왔기 때문입니다.
* **해결 방법**: 실행 스크립트를 `reachy_mini/` 저장소 바깥의 상위 폴더(`reachym_test/`)로 이동시킨 뒤 `--project .\reachy_mini` 옵션으로 실행합니다.
  ```powershell
  cd C:\Users\fall2\work\reachym_test
  uv run --project .\reachy_mini python .\face_tracking.py
  ```

### 2-2. `uv run` 실행 시 수동 설치한 패키지가 초기화되는 현상
* **원인**: `uv pip install`로 수동 설치한 패키지는 `pyproject.toml`에 기록되지 않으므로, 이후 `uv run`이 환경 동기화를 수행할 때 제거될 수 있습니다.
* **해결 방법**: 일회성 실행에 필요한 외부 라이브러리(`mcp`, `pyttsx3`, `opencv-python`)는 `uv run` 호출 시 **`--with <패키지명>`** 플래그로 주입하여 실행합니다.

### 2-3. `AttributeError: module 'cv2' has no attribute 'CascadeClassifier'`
* **원인**: 최신 OpenCV 5.0 프리릴리즈 버전이 설치되면서 구형 Haar Cascade API(`cv2.CascadeClassifier`)가 기본 빌드 경로에서 제외되었습니다.
* **해결 방법**: OpenCV 4.x 안정화 버전을 명시적으로 지정하여 실행합니다.
  ```powershell
  uv run --project .\reachy_mini --with "opencv-python<5.0" python .\face_tracking.py
  ```

---

## 3. MCP(Model Context Protocol) 서버 및 클라이언트 이슈

### 3-1. `ModuleNotFoundError: No module named 'mcp.server.fastmcp'`
* **에러 메시지**:
  ```text
  ModuleNotFoundError: No module named 'mcp.server.fastmcp'. This is mcp 2.x, where FastMCP was renamed to MCPServer
  ```
* **원인**: 설치된 `mcp` Python SDK가 2.x 이상으로 업데이트되면서 `FastMCP` 클래스 경로와 이름이 `MCPServer`로 변경되었습니다.
* **해결 방법**: 최신 MCP v2 표준 임포트 경로를 사용합니다.
  ```python
  from mcp.server.mcpserver import MCPServer
  mcp = MCPServer("ReachyMiniFullController")
  ```

### 3-2. `mcp.shared.exceptions.MCPError: Connection closed` (초기화 실패)
* **원인**:
  1. MCP의 `stdio` 통신은 표준 출력(`stdout`)으로 JSON-RPC 메시지를 주고받는데, `ReachyMini()` 초기화 로그나 Hugging Face 데이터셋 다운로드 메시지가 `stdout`으로 출력되어 프로토콜 파싱이 깨짐.
  2. 테스트 클라이언트에서 자식 프로세스로 `uv`를 중첩 호출하면서 실행 경로를 찾지 못해 서버 프로세스가 조기 종료됨.
* **해결 방법**:
  1. 서버 코드에서 `ReachyMini()` 및 `RecordedMoves()` 호출 시 **`contextlib.redirect_stdout(sys.stderr)`**로 감싸 모든 일반 로그를 `stderr`로 우회시킵니다.
  2. 클라이언트에서는 `uv`를 재호출하지 않고 현재 활성화된 파이썬 인터프리터 경로(`sys.executable`)와 서버 스크립트 절대 경로(`os.path.abspath`)를 `StdioServerParameters`에 직접 전달합니다.

### 3-3. `AttributeError: 'list' object has no attribute 'text'`
* **원인**: MCP 클라이언트의 `session.call_tool()` 및 `session.read_resource()` 반환 객체에서 `.content`(또는 `.contents`)는 단일 객체가 아니라 `TextContent` 요소들이 담긴 **리스트(`list`)**입니다.
* **해결 방법**: 반드시 인덱스 `0`을 지정하여 텍스트를 추출합니다.
  ```python
  # 도구 호출 결과 읽기
  print(res.content[0].text)

  # 리소스 조회 결과 읽기
  print(res.contents[0].text)
  ```

---

## 4. 공식 모션 라이브러리 및 시나리오 실행 이슈

### 4-1. `Error executing tool play_official_move` (`'happy'` 모션 실행 실패)
* **원인**: Hugging Face 공식 감정 라이브러리(`pollen-robotics/reachy-mini-emotions-library`)의 실제 키 이름에는 뒤에 번호가 붙어 있어 `'happy'`라는 이름은 존재하지 않습니다.
* **해결 방법**: 먼저 `list_official_moves(category="emotions")`를 호출하여 실제 등록된 모션 이름(`'cheerful1'`, `'amazed1'`, `'attentive1'`, `'enthusiastic1'` 등)을 확인한 뒤 정확한 이름으로 호출합니다.

### 4-2. `.cfg` 시나리오 파싱 시 리스트 인덱싱 누락 오류
* **원인**: `line.split("|")`로 분리한 토큰 리스트 `parts`에서 명령어(`parts[0]`)와 인자(`parts[1]`, `parts[2]` 등)를 꺼낼 때 인덱스가 누락되면 `AttributeError`나 `TypeError`가 발생합니다.
* **해결 방법**: `cmd = parts[0].lower()`, `parts[1]`, `parts[2]`와 같이 명시적 인덱싱을 적용하고 `try-except` 블록으로 감싸 어느 `.cfg` 파일의 몇 번째 줄에서 오류가 발생했는지 명확히 반환하도록 개선했습니다.
