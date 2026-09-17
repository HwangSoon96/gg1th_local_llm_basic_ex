# 미션 : 문제 해결
###############################################
# WSL Linux STT → Ollama → TTS 음성 챗 앱
#
# 마이크 음성 입력
# → STT: faster-whisper
# → LLM: Ollama gemma4:e4b
# → TTS: edge-tts
# → 출력: mpg123 또는 pygame
#
# 설치:
# sudo apt install -y libportaudio2 portaudio19-dev libasound2-dev \
#   libpulse0 pulseaudio-utils libasound2-plugins alsa-utils
#
# mkdir -p models/piper

# wget -O models/piper/piper-kss-korean.onnx \
# https://huggingface.co/neurlang/piper-onnx-kss-korean/resolve/main/piper-kss-korean.onnx

# wget -O models/piper/piper-kss-korean.onnx.json \
# https://huggingface.co/neurlang/piper-onnx-kss-korean/resolve/main/piper-kss-korean.onnx.json
###############################################
###############################################
# WSL Linux STT → Ollama → Piper TTS 음성 챗 앱
#
# 마이크 음성 입력
# → STT: faster-whisper
# → LLM: Ollama / gemma4:e4b
# → TTS: Piper
# → 출력: paplay / aplay / pygame
#
# 설치:
# sudo apt install -y libportaudio2 portaudio19-dev libasound2-dev \
#   libpulse0 pulseaudio-utils libasound2-plugins alsa-utils
# uv pip install ollama sounddevice scipy faster-whisper pygame piper-tts

# WSL에서 마이크 인식시키기
# pactl list short sources
# pactl info | grep "Default Source"
# pactl set-default-source RDPSource
###############################################

import os
import platform
import shutil
import subprocess
import time
from pathlib import Path

# pygame 안내 문구 숨기기
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

def is_wsl() -> bool:
    """현재 실행 환경이 WSL인지 확인한다."""
    try:
        release = platform.uname().release.lower()
        return "microsoft" in release or "wsl" in release
    except Exception:
        return False


# WSL에서는 pygame이 ALSA 대신 PulseAudio를 우선 사용하도록 설정한다.
# 반드시 pygame import 전에 설정해야 한다.
if is_wsl():
    os.environ.setdefault("SDL_AUDIODRIVER", "pulse")


import ollama
import sounddevice as sd
from scipy.io.wavfile import write
from faster_whisper import WhisperModel
import pygame


# =========================
# 기본 설정
# =========================

OLLAMA_MODEL = "gemma4:e2b"
# OLLAMA_MODEL = "llama3.2:3b"
# OLLAMA_MODEL = "llama3.2:1b"

SAMPLE_RATE = 44100
RECORD_SECONDS = 5

WHISPER_MODEL_SIZE = "base"      # tiny, base, small, medium, large-v3
WHISPER_DEVICE = "cpu"           # CUDA 가능 시 "cuda"
WHISPER_COMPUTE_TYPE = "int8"    # CUDA 사용 시 "float16"

VOICE_DIR = Path("./voice")
INPUT_WAV_FILE = VOICE_DIR / "input.wav"
OUTPUT_WAV_FILE = VOICE_DIR / "answer.wav"

# Piper 모델
PIPER_MODEL_FILE = Path("./models/piper/piper-kss-korean.onnx")
PIPER_CONFIG_FILE = Path("./models/piper/piper-kss-korean.onnx.json")

# 이 KSS 한국어 모델은 phoneme_type=pygoruut 규격이라, 파이썬 piper-tts 로는 실행할 수 없다.
# neurlang 계열 Rust 런타임(piper-rs)의 synth_stdin 예제 바이너리로 합성한다.
# (빌드: piper-rs 디렉터리에서 `cargo build --release --example synth_stdin`)
PIPER_RS_BIN = (
    Path(__file__).resolve().parent.parent
    / "piper-rs" / "target" / "release" / "examples" / "synth_stdin"
)

# 특정 마이크 장치를 직접 지정해야 하면 숫자로 설정한다.
# None이면 시스템 기본 입력 장치를 사용한다.
INPUT_DEVICE_INDEX = None

# 대화 맥락 유지 길이
MAX_HISTORY_MESSAGES = 10


# =========================
# STT 모델 로드
# =========================

print("STT 모델 로딩 중...")

stt_model = WhisperModel(
    WHISPER_MODEL_SIZE,
    device=WHISPER_DEVICE,
    compute_type=WHISPER_COMPUTE_TYPE
)

print("STT 모델 로딩 완료")


# =========================
# 대화 히스토리
# =========================

messages = [
    {
        "role": "system",
        "content": (
            "너는 한국어로 간결하고 명확하게 답변하는 로컬 AI 비서다. "
            "사용자의 음성 질문에 자연스럽게 답변하라. "
            "답변은 음성으로 들었을 때 이해하기 쉽도록 너무 길지 않게 작성하라."
        )
    }
]


def check_piper_files() -> None:
    """Piper 모델 파일 존재 여부를 확인한다."""

    if not PIPER_RS_BIN.exists():
        raise RuntimeError(
            f"piper-rs 바이너리를 찾을 수 없습니다: {PIPER_RS_BIN}\n"
            "piper-rs 디렉터리에서 "
            "`cargo build --release --example synth_stdin` 로 빌드하세요."
        )

    if not PIPER_MODEL_FILE.exists():
        raise FileNotFoundError(
            f"Piper 모델 파일을 찾을 수 없습니다: {PIPER_MODEL_FILE}"
        )

    if not PIPER_CONFIG_FILE.exists():
        raise FileNotFoundError(
            f"Piper 설정 파일을 찾을 수 없습니다: {PIPER_CONFIG_FILE}"
        )


def show_audio_devices() -> None:
    """현재 WSL/Linux에서 인식되는 오디오 장치를 출력한다."""

    print("\n[오디오 장치 목록]")
    print(sd.query_devices())
    print(f"\n기본 장치: {sd.default.device}")


def record_audio(output_path: Path, seconds: int = RECORD_SECONDS) -> None:
    """마이크 음성을 WAV 파일로 저장한다."""

    output_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"\n{seconds}초 동안 말하세요.")

    try:
        sd.check_input_settings(
            device=INPUT_DEVICE_INDEX,
            samplerate=SAMPLE_RATE,
            channels=1
        )
    except Exception as e:
        print("\n입력 장치 설정 확인 중 오류가 발생했습니다.")
        print(f"{type(e).__name__}: {e}")
        print("장치 목록을 확인한 뒤 INPUT_DEVICE_INDEX를 지정해야 할 수 있습니다.")
        raise

    audio = sd.rec(
        int(seconds * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="float32",
        device=INPUT_DEVICE_INDEX
    )

    sd.wait()

    write(output_path, SAMPLE_RATE, audio)

    print(f"녹음 완료: {output_path}")


def transcribe_audio(audio_path: Path) -> str:
    """WAV 음성 파일을 텍스트로 변환한다."""

    if not audio_path.exists():
        raise FileNotFoundError(f"음성 파일을 찾을 수 없습니다: {audio_path}")

    print("\nSTT 변환 중...")

    segments, info = stt_model.transcribe(
        str(audio_path),
        language="ko",
        beam_size=5
    )

    text = " ".join(segment.text.strip() for segment in segments).strip()

    return text


def trim_messages() -> None:
    """대화 히스토리가 너무 길어지지 않도록 최근 메시지만 유지한다."""

    global messages

    system_message = messages[0]
    recent_messages = messages[1:][-MAX_HISTORY_MESSAGES:]

    messages = [system_message] + recent_messages


def ask_ollama(user_text: str) -> str:
    """Ollama 모델에 질문하고 답변을 받는다."""

    messages.append(
        {
            "role": "user",
            "content": user_text
        }
    )

    trim_messages()

    print("\nOllama 답변 생성 중...")

    response = ollama.chat(
        model=OLLAMA_MODEL,
        messages=messages,
        options={
            "temperature": 0.3,
            "top_p": 0.9,
            "num_predict": 512
        }
    )

    try:
        answer = response.message.content
    except AttributeError:
        answer = response["message"]["content"]

    answer = answer.strip()

    messages.append(
        {
            "role": "assistant",
            "content": answer
        }
    )

    return answer


def text_to_speech_with_piper(text: str, output_path: Path) -> None:
    """piper-rs(synth_stdin)로 텍스트 답변을 WAV 음성 파일로 변환한다.

    - 인자로 config(.json) 경로와 출력 wav 경로를 주고, 변환할 텍스트는 stdin 으로 넘긴다.
    - piper-rs 는 pygoruut 포나이징을 위해 goruut 데몬을 별도 프로세스로 띄우는데,
      그 데몬이 부모의 stdout/stderr 파이프를 물고 계속 살아있다. 따라서 capture_output
      (PIPE)로 받으면 EOF 가 오지 않아 그대로 멈춘다. 로그 파일로 리다이렉트해서 회피한다.
    - goruut 데몬 기동 때문에 각 실행의 첫 합성은 수 초~수십 초 걸릴 수 있어 timeout 을 넉넉히 준다.
    """

    if not text.strip():
        raise ValueError("Piper로 변환할 텍스트가 비어 있습니다.")

    check_piper_files()

    output_path.parent.mkdir(parents=True, exist_ok=True)

    print("\nPiper(piper-rs) TTS 변환 중...")

    command = [
        str(PIPER_RS_BIN),
        str(PIPER_CONFIG_FILE),
        str(output_path),
    ]

    log_path = output_path.with_suffix(".piper.log")

    try:
        with open(log_path, "w") as log_file:
            result = subprocess.run(
                command,
                input=text.encode("utf-8"),
                stdout=log_file,   # PIPE 금지: goruut 데몬이 파이프를 물면 멈춘다
                stderr=log_file,
                timeout=180,
            )
    except subprocess.TimeoutExpired:
        raise RuntimeError(
            "piper-rs 합성이 시간 내에 끝나지 않았습니다. "
            f"(첫 실행 시 goruut 데몬 다운로드/기동이 오래 걸릴 수 있음) 로그: {log_path}"
        )

    if result.returncode != 0 or not output_path.exists():
        log_text = ""
        try:
            log_text = log_path.read_text(errors="replace")
        except Exception:
            pass
        print("\npiper-rs 실행 실패")
        print(log_text)
        raise RuntimeError("Piper(piper-rs) TTS 변환에 실패했습니다.")

    print(f"Piper(piper-rs) TTS 파일 저장 완료: {output_path}")


def play_with_paplay(audio_path: Path) -> bool:
    """PulseAudio paplay로 WAV 파일을 재생한다."""

    if shutil.which("paplay") is None:
        return False

    try:
        subprocess.run(["paplay", str(audio_path)], check=True)
        return True
    except Exception as e:
        print("\npaplay 재생 실패")
        print(f"{type(e).__name__}: {e}")
        return False


def play_with_aplay(audio_path: Path) -> bool:
    """ALSA aplay로 WAV 파일을 재생한다."""

    if shutil.which("aplay") is None:
        return False

    try:
        subprocess.run(["aplay", str(audio_path)], check=True)
        return True
    except Exception as e:
        print("\naplay 재생 실패")
        print(f"{type(e).__name__}: {e}")
        return False


def play_with_pygame(audio_path: Path) -> bool:
    """pygame으로 WAV 파일을 재생한다."""

    try:
        pygame.mixer.init()
        pygame.mixer.music.load(str(audio_path))
        pygame.mixer.music.play()

        while pygame.mixer.music.get_busy():
            time.sleep(0.1)

        pygame.mixer.quit()
        return True

    except Exception as e:
        print("\npygame 재생 실패")
        print(f"{type(e).__name__}: {e}")

        try:
            pygame.mixer.quit()
        except Exception:
            pass

        return False


def play_audio(audio_path: Path) -> None:
    """WAV 파일을 재생한다."""

    if not audio_path.exists():
        raise FileNotFoundError(f"재생할 음성 파일을 찾을 수 없습니다: {audio_path}")

    print("\n음성 출력 중...")

    # WSL에서는 PulseAudio 기반 paplay가 가장 먼저 시도할 만하다.
    if play_with_paplay(audio_path):
        print("음성 출력 완료")
        return

    # 일반 Linux/ALSA 환경에서는 aplay가 동작할 수 있다.
    if play_with_aplay(audio_path):
        print("음성 출력 완료")
        return

    # 마지막 fallback
    if play_with_pygame(audio_path):
        print("음성 출력 완료")
        return

    print("\n자동 재생에 실패했습니다.")
    print(f"생성된 파일을 직접 열어 재생하세요: {audio_path}")


def run_voice_turn() -> None:
    """음성 입력 1회에 대한 STT → Ollama → Piper TTS → 출력 흐름을 실행한다."""

    # 1. 마이크 녹음
    record_audio(INPUT_WAV_FILE)

    # 2. STT
    user_text = transcribe_audio(INPUT_WAV_FILE)

    if not user_text:
        print("\n음성을 인식하지 못했습니다.")
        return

    print("\n사용자 음성 인식 결과:")
    print(user_text)

    # 3. Ollama 답변
    answer = ask_ollama(user_text)

    if not answer:
        print("\nOllama 답변이 비어 있습니다.")
        return

    print("\nAI 답변:")
    print(answer)

    # 4. Piper TTS
    text_to_speech_with_piper(answer, OUTPUT_WAV_FILE)

    # 5. 음성 출력
    play_audio(OUTPUT_WAV_FILE)


def main() -> None:
    """음성 챗 앱 메인 루프."""

    print("\nWSL Linux 음성 Ollama + Piper 챗 앱 시작")
    print(f"실행 환경: {platform.system()}")
    print(f"WSL 여부: {is_wsl()}")
    print(f"Ollama 모델: {OLLAMA_MODEL}")
    print(f"Whisper 모델: {WHISPER_MODEL_SIZE}")
    print(f"Piper 모델: {PIPER_MODEL_FILE}")
    print(f"녹음 시간: {RECORD_SECONDS}초")

    try:
        check_piper_files()
    except Exception as e:
        print("\nPiper 설정 오류")
        print(f"{type(e).__name__}: {e}")
        return

    show_audio_devices()

    print("\n명령:")
    print("Enter 또는 r : 음성 녹음 시작")
    print("d          : 오디오 장치 목록 다시 보기")
    print("q          : 종료")

    while True:
        command = input("\n명령 입력: ").strip().lower()

        if command == "q":
            print("종료합니다.")
            break

        if command == "d":
            show_audio_devices()
            continue

        if command not in ["", "r"]:
            print("Enter 또는 r을 입력하면 녹음을 시작합니다. q는 종료입니다.")
            continue

        try:
            run_voice_turn()

        except KeyboardInterrupt:
            print("\n사용자에 의해 중단되었습니다.")
            break

        except ollama.ResponseError as e:
            print("\nOllama 응답 오류가 발생했습니다.")
            print(e)
            print(f"\n모델 설치 여부를 확인하세요: ollama pull {OLLAMA_MODEL}")

        except ConnectionError as e:
            print("\nOllama 서버 연결 오류가 발생했습니다.")
            print(e)
            print("Ollama가 실행 중인지 확인하세요: ollama serve")

        except Exception as e:
            print("\n오류 발생")
            print(f"{type(e).__name__}: {e}")


if __name__ == "__main__":
    main()