###############################################
# WSL Linux STT → Ollama → TTS 음성 챗 앱
#
# 마이크 음성 입력
# → STT: faster-whisper
# → LLM: Ollama
# → TTS: edge-tts
# → 출력: mpg123 또는 pygame
#
# 설치:
# sudo apt install -y libportaudio2 portaudio19-dev libasound2-dev \
#   libpulse0 pulseaudio-utils libasound2-plugins mpg123
#
# pip install ollama sounddevice scipy faster-whisper edge-tts pygame

# WSL에서 마이크 인식시키기
# pactl list short sources
# pactl info | grep "Default Source"
# pactl set-default-source RDPSource
###############################################

import asyncio
import os
import platform
import shutil
import subprocess
import time
from pathlib import Path

# pygame 안내 문구 숨기기
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

# WSLg 마이크 입력 source 지정
os.environ["PULSE_SOURCE"] = "RDPSource"


def is_wsl() -> bool:
    """현재 실행 환경이 WSL인지 확인한다."""
    try:
        release = platform.uname().release.lower()
        return "microsoft" in release or "wsl" in release
    except Exception:
        return False


# WSL에서는 pygame이 ALSA 대신 PulseAudio를 우선 사용하도록 설정한다.
if is_wsl():
    os.environ.setdefault("SDL_AUDIODRIVER", "pulse")


import ollama
from faster_whisper import WhisperModel
import edge_tts
import pygame


# =========================
# 기본 설정
# =========================

OLLAMA_MODEL = "exaone3.5:7.8b"
# OLLAMA_MODEL = "gemma4:e4b"
# OLLAMA_MODEL = "llama3.2:3b"

SAMPLE_RATE = 44100
RECORD_SECONDS = 5

WHISPER_MODEL_SIZE = "base"
WHISPER_DEVICE = "cpu"
WHISPER_COMPUTE_TYPE = "int8"

TTS_VOICE = "ko-KR-SunHiNeural"

VOICE_DIR = Path("./voice")
INPUT_WAV_FILE = VOICE_DIR / "input.wav"
OUTPUT_MP3_FILE = VOICE_DIR / "answer.mp3"

PULSE_SOURCE = "RDPSource"

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


def show_pulse_sources() -> None:
    """PulseAudio source 목록을 출력한다."""

    print("\n[PulseAudio 입력 source 목록]")

    try:
        subprocess.run(
            ["pactl", "list", "sources", "short"],
            check=False
        )

        print("\n[기본 입력 source]")
        subprocess.run(
            ["pactl", "get-default-source"],
            check=False
        )

    except Exception as e:
        print("PulseAudio source 조회 실패")
        print(f"{type(e).__name__}: {e}")


def set_default_source() -> None:
    """PulseAudio 기본 입력 source를 RDPSource로 설정한다."""

    try:
        subprocess.run(
            ["pactl", "set-default-source", PULSE_SOURCE],
            check=True
        )
    except Exception as e:
        print("\n기본 입력 source 설정 실패")
        print(f"{type(e).__name__}: {e}")
        print("pactl list sources short 결과에서 RDPSource가 있는지 확인해야 합니다.")
        raise


def record_audio(output_path: Path, seconds: int = RECORD_SECONDS) -> None:
    """parecord를 사용해 WSLg RDPSource에서 음성을 녹음한다."""

    output_path.parent.mkdir(parents=True, exist_ok=True)

    if shutil.which("parecord") is None:
        raise RuntimeError(
            "parecord 명령을 찾을 수 없습니다. "
            "sudo apt install -y pulseaudio-utils 를 실행하세요."
        )

    print(f"\n{seconds}초 동안 말하세요.")
    print(f"사용 PulseAudio source: {PULSE_SOURCE}")

    set_default_source()

    command = [
        "timeout",
        str(seconds),
        "parecord",
        f"--device={PULSE_SOURCE}",
        "--file-format=wav",
        f"--rate={SAMPLE_RATE}",
        "--channels=1",
        str(output_path)
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True
    )

    # timeout은 정상 종료 시에도 환경에 따라 124를 반환할 수 있다.
    if result.returncode not in [0, 124]:
        print("\nparecord 실행 실패")
        print("[stdout]")
        print(result.stdout)
        print("[stderr]")
        print(result.stderr)
        raise RuntimeError("녹음에 실패했습니다.")

    if not output_path.exists() or output_path.stat().st_size == 0:
        raise RuntimeError("녹음 파일이 생성되지 않았거나 비어 있습니다.")

    print(f"녹음 완료: {output_path}")

    check_wav_volume(output_path)


def check_wav_volume(audio_path: Path) -> None:
    """WAV 파일의 음량을 확인한다."""

    try:
        from scipy.io.wavfile import read
        import numpy as np

        sr, audio = read(audio_path)

        audio_f = audio.astype("float32")

        peak = float(np.max(np.abs(audio_f)))
        rms = float(np.sqrt(np.mean(audio_f ** 2)))

        print(f"녹음 파일 sample_rate: {sr}")
        print(f"녹음 음량 peak: {peak:.2f}")
        print(f"녹음 음량 rms : {rms:.2f}")

        if peak < 300:
            print("\n주의: 녹음 파일의 음량이 매우 작습니다.")
            print("RDPSource는 잡혔지만 실제 마이크 음성이 WSL로 들어오지 않는 상태일 수 있습니다.")

    except Exception as e:
        print("\n녹음 음량 확인 실패")
        print(f"{type(e).__name__}: {e}")


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


async def text_to_speech(text: str, output_path: Path) -> None:
    """텍스트 답변을 MP3 음성 파일로 변환한다."""

    if not text.strip():
        raise ValueError("TTS로 변환할 텍스트가 비어 있습니다.")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    print("\nTTS 변환 중...")

    communicate = edge_tts.Communicate(
        text=text,
        voice=TTS_VOICE,
        rate="+0%",
        volume="+0%"
    )

    await communicate.save(str(output_path))

    print(f"TTS 파일 저장 완료: {output_path}")


def play_with_mpg123(audio_path: Path) -> bool:
    """mpg123으로 MP3 파일을 재생한다."""

    if shutil.which("mpg123") is None:
        return False

    try:
        command = ["mpg123", "-q", "-o", "pulse", str(audio_path)]

        subprocess.run(command, check=True)
        return True

    except Exception as e:
        print("\nmpg123 재생 실패")
        print(f"{type(e).__name__}: {e}")
        return False


def play_with_pygame(audio_path: Path) -> bool:
    """pygame으로 MP3 파일을 재생한다."""

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
    """MP3 파일을 재생한다."""

    if not audio_path.exists():
        raise FileNotFoundError(f"재생할 음성 파일을 찾을 수 없습니다: {audio_path}")

    print("\n음성 출력 중...")

    if play_with_mpg123(audio_path):
        print("음성 출력 완료")
        return

    if play_with_pygame(audio_path):
        print("음성 출력 완료")
        return

    print("\n자동 재생에 실패했습니다.")
    print(f"생성된 파일을 직접 열어 재생하세요: {audio_path}")


def run_voice_turn() -> None:
    """음성 입력 1회에 대한 STT → Ollama → TTS → 출력 흐름을 실행한다."""

    # 1. 마이크 녹음
    record_audio(INPUT_WAV_FILE)

    # 2. STT
    user_text = transcribe_audio(INPUT_WAV_FILE)

    if not user_text:
        print("\n음성을 인식하지 못했습니다.")
        print("voice/input.wav에 실제 음성이 들어갔는지 먼저 확인해야 합니다.")
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

    # 4. TTS
    asyncio.run(text_to_speech(answer, OUTPUT_MP3_FILE))

    # 5. 음성 출력
    play_audio(OUTPUT_MP3_FILE)


def main() -> None:
    """음성 챗 앱 메인 루프."""

    print("\nWSL Linux 음성 Ollama 챗 앱 시작")
    print(f"실행 환경: {platform.system()}")
    print(f"WSL 여부: {is_wsl()}")
    print(f"Ollama 모델: {OLLAMA_MODEL}")
    print(f"Whisper 모델: {WHISPER_MODEL_SIZE}")
    print(f"녹음 시간: {RECORD_SECONDS}초")
    print(f"PulseAudio source: {PULSE_SOURCE}")

    show_pulse_sources()

    print("\n명령:")
    print("Enter 또는 r : 음성 녹음 시작")
    print("d          : PulseAudio source 목록 다시 보기")
    print("q          : 종료")

    while True:
        command = input("\n명령 입력: ").strip().lower()

        if command == "q":
            print("종료합니다.")
            break

        if command == "d":
            show_pulse_sources()
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