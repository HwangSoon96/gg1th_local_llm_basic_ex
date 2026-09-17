###############################################
# STT → Ollama → TTS
# 음성 파일 입력 → 텍스트
# → Ollama: 텍스트 질문 → 텍스트 답변
# → TTS: 텍스트 답변 → 음성 파일 생성 및 재생
#
# STT : faster-whisper
# TTS : edge-tts
#
# 설치:
# pip install ollama faster-whisper edge-tts pygame
###############################################

import asyncio
import os
import time
from pathlib import Path

import ollama
from faster_whisper import WhisperModel
import edge_tts
import pygame


# =========================
# 기본 설정
# =========================

OLLAMA_MODEL = "exaone3.5:7.8b"
# 테스트가 무거우면 아래 모델로 먼저 확인
# OLLAMA_MODEL = "llama3.2:3b"

AUDIO_FILE = Path("./voice/voice1.mp3")
OUTPUT_TTS_FILE = Path("./voice/answer.mp3")

WHISPER_MODEL_SIZE = "base"    # tiny, base, small, medium, large-v3
WHISPER_DEVICE = "cpu"         # RTX 3080이면 "cuda" 사용 가능
WHISPER_COMPUTE_TYPE = "int8"  # cuda 사용 시 "float16" 권장

TTS_VOICE = "ko-KR-SunHiNeural"


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
            "사용자의 음성 질문을 텍스트로 변환한 내용을 바탕으로 자연스럽게 답변하라."
        )
    }
]


def transcribe_audio(audio_path: Path) -> str:
    """음성 파일을 텍스트로 변환한다."""

    if not audio_path.exists():
        raise FileNotFoundError(f"음성 파일을 찾을 수 없습니다: {audio_path}")

    print(f"\n음성 파일 읽는 중: {audio_path}")
    print("STT 변환 중...")

    segments, info = stt_model.transcribe(
        str(audio_path),
        language="ko",
        beam_size=5
    )

    text = " ".join(segment.text.strip() for segment in segments).strip()

    return text


def ask_ollama(user_text: str) -> str:
    """Ollama 모델에 질문하고 답변을 받는다."""

    messages.append({
        "role": "user",
        "content": user_text
    })

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

    # ollama-python 버전에 따라 객체/딕셔너리 접근 모두 대비
    try:
        answer = response.message.content
    except AttributeError:
        answer = response["message"]["content"]

    answer = answer.strip()

    messages.append({
        "role": "assistant",
        "content": answer
    })

    return answer


async def text_to_speech(text: str, output_path: Path) -> None:
    """텍스트 답변을 음성 MP3 파일로 변환한다."""

    print("\nTTS 변환 중...")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    communicate = edge_tts.Communicate(
        text=text,
        voice=TTS_VOICE,
        rate="+0%",
        volume="+0%"
    )

    await communicate.save(str(output_path))

    print(f"TTS 파일 저장 완료: {output_path}")


def play_audio(audio_path: Path) -> None:
    """WSL2에서는 Windows 기본 플레이어로 MP3 파일을 연다."""

    if not audio_path.exists():
        raise FileNotFoundError(f"재생할 음성 파일을 찾을 수 없습니다: {audio_path}")

    print("\n음성 출력 중...")

    try:
        # WSL2 환경이면 Windows 경로로 변환 후 Windows 기본 플레이어 실행
        import subprocess

        linux_path = str(audio_path.resolve())
        windows_path = subprocess.check_output(
            ["wslpath", "-w", linux_path],
            text=True
        ).strip()

        subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-Command",
                f"Start-Process -FilePath '{windows_path}'"
            ],
            check=True
        )

        print(f"Windows 기본 플레이어로 재생 파일을 열었습니다: {windows_path}")

    except Exception as e:
        print("Windows 플레이어 실행에 실패했습니다.")
        print(e)

def main():
    print("\n파일 기반 음성 Ollama 앱 시작")

    try:
        # 1. 음성 파일 → 텍스트
        user_text = transcribe_audio(AUDIO_FILE)

        if not user_text:
            print("음성을 인식하지 못했습니다.")
            return

        print("\n사용자 음성 인식 결과:")
        print(user_text)

        # 2. 텍스트 → Ollama 답변
        answer = ask_ollama(user_text)

        print("\nAI 답변:")
        print(answer)

        # 3. 답변 텍스트 → 음성 파일
        asyncio.run(text_to_speech(answer, OUTPUT_TTS_FILE))

        # 4. 음성 출력
        play_audio(OUTPUT_TTS_FILE)

    except Exception as e:
        print(f"\n오류 발생: {type(e).__name__}")
        print(e)


if __name__ == "__main__":
    main()