# 🎙️ 사용자 녹음 음성(.wav/.mp3) 재생 기능 확장 가이드 (FEATURE_VOICE_SUPPORT.md)

이 문서는 `.cfg` 시나리오 파일에서 **사용자가 직접 녹음한 목소리 파일(`.wav`, `.mp3`, `.m4a` 등)을 재생**하고, 음성이 출력되는 동안 로봇의 움직임(감정·춤·고개 끄덕임)과 자연스럽게 어우러지도록 확장하는 설계 및 구현 방법을 안내합니다.

---

## 1. 기능 개요 및 `.cfg` 문법 확장

기존 `sound` 명령어를 확장하여 **동기 재생(음성이 끝날 때까지 대기)**과 **비동기 재생(음성을 틀어둔 채 다음 로봇 동작을 동시에 실행)** 두 가지 모드를 지원하도록 설계합니다.

### 확장된 `.cfg` 명령어 문법
```ini
# 1. 기본(동기) 재생: 음성 파일 재생이 끝난 후 다음 줄 실행
voice | sounds/my_greeting.wav

# 2. 비동기(동시) 재생: 음성을 재생하면서 즉시 다음 줄의 로봇 움직임을 동시에 수행
voice | sounds/my_greeting.wav | async
```

### 실전 시나리오 적용 예시 (`scenarios/custom_voice_greeting.cfg`)
```ini
# 목적: 내가 직접 녹음한 환영 인사를 들려주며 반갑게 몸을 움직이는 복합 동작
power | wake_up

# 녹음된 내 목소리를 백그라운드로 재생 시작 (async)
voice | sounds/hello_owner.wav | async

# 목소리가 나오는 동안 동시에 고개 끄덕임 및 기쁨 모션 실행
move | 12 | 0 | 18 | 0 | 0 | 0.8 | -0.8 | 0.45
move | 12 | 0 | -5 | 0 | 0 | -0.3 | 0.3 | 0.45
emotion | cheerful1

reset | 0.8
```

---

## 2. 권장 폴더 구조 및 오디오 파일 준비

프로젝트 루트에 `sounds/` 폴더를 생성하고 녹음한 음성 파일을 배치합니다.

```text
reachym_test/
 ├── sounds/                      # 사용자 녹음 음성 파일 저장 폴더
 │    ├── hello_owner.wav         # 직접 녹음한 인사 음성 (권장: 16kHz~44.1kHz WAV)
 │    └── cheer_up.mp3            # 응원 메시지 음성
 ├── scenarios/
 │    └── custom_voice_greeting.cfg
 ├── reachy_mcp_server.py
 └── FEATURE_VOICE_SUPPORT.md
```

### 💡 녹음 파일 포맷 팁
* **가장 안정적인 포맷**: 별도 외부 코덱 없이 Windows 기본 오디오와 Reachy Mini SDK 모두에서 즉시 재생되는 **PCM `.wav` (16-bit)** 형식을 권장합니다.
* **MP3 / M4A 지원**: 스마트폰이나 Windows '녹음기' 앱으로 녹음한 `.mp3` 또는 `.m4a` 파일을 그대로 쓰려면 실행 시 `--with pygame` 옵션을 추가하면 변환 없이 즉시 재생됩니다.

---

## 3. `reachy_mcp_server.py` 구현 코드 업데이트

`reachy_mcp_server.py`에 **`play_recorded_voice`** 도구를 추가하고 `run_scenario_cfg` 파서가 `voice` 명령어를 처리하도록 업데이트합니다.

### ① `play_recorded_voice` MCP 도구 추가
```python
import threading

@mcp.tool()
def play_recorded_voice(file_path: str, async_play: bool = False) -> str:
    """사용자가 녹음한 음성 파일(.wav, .mp3 등)을 로봇(또는 PC) 스피커로 재생합니다.
    async_play=True 설정 시 음성 재생과 동시에 다음 로봇 동작을 병행 실행할 수 있습니다.
    """
    # 경로 탐색 (현재 폴더 -> sounds/ 폴더 순으로 확인)
    target_path = file_path
    if not os.path.exists(target_path):
        alt_path = os.path.join("sounds", file_path)
        if os.path.exists(alt_path):
            target_path = alt_path
        else:
            return f"오류: 음성 파일을 찾을 수 없습니다 -> '{file_path}'"

    abs_path = os.path.abspath(target_path)
    mini = get_mini()

    def _play_worker():
        # 1순위: Reachy Mini SDK 미디어 서버 재생 (실물 기기 호환)
        try:
            mini.media.play_sound(abs_path)
            return
        except Exception:
            pass

        # 2순위: pygame 믹서 재생 (시뮬레이터 환경에서 .mp3, .wav, .ogg 모두 지원)
        try:
            import pygame
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            pygame.mixer.music.load(abs_path)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                time.sleep(0.05)
            return
        except ImportError:
            pass

        # 3순위: Windows 내장 winsound (.wav 전용 폴백)
        if abs_path.lower().endswith(".wav") and sys.platform == "win32":
            import winsound
            winsound.PlaySound(abs_path, winsound.SND_FILENAME)

    if async_play:
        threading.Thread(target=_play_worker, daemon=True).start()
        return f"녹음 음성 비동기(동시) 재생 시작: '{target_path}'"
    else:
        _play_worker()
        return f"녹음 음성 재생 완료: '{target_path}'"
```

### ② `run_scenario_cfg` 파서 내부에 `voice` 분기 추가
`reachy_mcp_server.py`의 `run_scenario_cfg` 함수 안의 `if / elif` 문에 아래 분기를 추가합니다.

```python
elif cmd == "voice" and len(parts) >= 2:
    voice_file = parts[1]
    is_async = len(parts) >= 3 and parts[2].lower() == "async"
    play_recorded_voice(file_path=voice_file, async_play=is_async)
```

---

## 4. 실행 방법 (`--with pygame` 추가)

MP3와 WAV 파일을 모두 안정적으로 재생하기 위해 `uv run` 명령어에 `--with pygame`을 포함해 실행합니다.

```powershell
# 1. sounds 폴더 생성 (최초 1회)
mkdir C:\Users\fall2\work\reachym_test\sounds

# 2. 녹음된 음성 파일을 sounds\hello_owner.wav 로 저장 후 시나리오 실행
cd C:\Users\fall2\work\reachym_test
uv run --project .\reachy_mini --with mcp --with pygame python .\run_cfg_client.py custom_voice_greeting.cfg
```

---

## 5. LLM 에이전트 활용 시나리오

이 도구가 MCP 서버에 등록되면 LLM에게 다음과 같은 자연어 지시를 내릴 수 있습니다.
* *"내 목소리로 녹음된 `hello_owner.wav` 파일을 틀면서 동시에 반갑게 춤춰줘."*
* LLM은 내부적으로 `play_recorded_voice(file_path="hello_owner.wav", async_play=True)`와 `play_official_move(move_name="groovy_sway_and_roll", category="dances")`를 연속 호출하여, **사용자의 실제 목소리가 나오는 동안 로봇이 리듬에 맞춰 움직이는 연출**을 자동으로 만들어냅니다.
