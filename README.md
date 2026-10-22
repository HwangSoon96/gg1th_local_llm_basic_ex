<div align="center">

# gg1th_local_llm_basic_ex

**Ollama 로컬 LLM 활용 기초 — 멀티모달 · 음성 챗, FastAPI 웹 서비스, React 기초**

![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![uv](https://img.shields.io/badge/uv-package%20manager-DE5FE9?logo=uv&logoColor=white)
![Ollama](https://img.shields.io/badge/Ollama-local%20LLM-000000?logo=ollama&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-D71F00?logo=sqlalchemy&logoColor=white)
![Oracle](https://img.shields.io/badge/Oracle-DB-F80000?logo=oracle&logoColor=white)
![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black)

</div>

<br>

## 실습 구성

### 1. Ollama 기초 — `ollama_basic/`

| 파일 | 내용 |
|---|---|
| `1.ollama_test.py` | Ollama REST API(`/api/generate`) 직접 호출 — `qwen3.5:9b` 등 모델 비교 |
| `2-1.ai_docent.py` | 이미지 → 텍스트 AI 도슨트 (`ollama` 라이브러리) |
| `2-2.ai_docent_qwen3-v1.py` | 비전 모델 `qwen3-vl:8b`로 이미지 설명 |
| `2-3.image_draw.py` | 텍스트 → 이미지 생성 (`x/flux2-klein`, macOS 전용) |
| `3-1.mp3_stt_tts_winplayer.py` | 음성 파일 → STT(faster-whisper) → Ollama → TTS(edge-tts) 재생 (Windows) |
| `3-2.mp3_stt_tts_linuxplayer.py` | 같은 파이프라인의 Linux 재생 버전 |
| `3-3.voice_chat_stt.py` | 마이크 입력 실시간 음성 챗 (WSL) |
| `3-4.voice_chat_piper.py` | TTS를 로컬 Piper(한국어 KSS 음성)로 교체한 음성 챗 |
| `gpu_test.ipynb` | GPU 인식 확인 |

```
마이크 / 음성 파일 → faster-whisper(STT) → Ollama(LLM) → edge-tts · Piper(TTS) → 스피커
```

### 2. FastAPI 기초 — `fastapi_basic/`

- 경로 · 쿼리 파라미터, Pydantic 요청 / 응답 모델(`response_model`)

### 3. Todo 웹 앱 — `todos_app/`

- FastAPI + Jinja2 템플릿 + SQLAlchemy ORM으로 할 일 추가 · 수정 · 삭제(CRUD)
- DB는 Oracle(`oracle+oracledb`) — `.env_example`을 `.env`로 복사해 접속 정보 입력

### 4. React 기초 — `react_basic/`

- Vite + React — 컴포넌트, `useState`, 조건부 · 리스트 렌더링, `useEffect`
- `OllamaChat.jsx`: 로컬 FastAPI(`/chat`)를 호출하는 채팅 컴포넌트

<br>

## 시작하기

### 사전 요구사항

- [Ollama](https://ollama.com/) + 사용할 모델 (`ollama pull qwen3.5:9b` 등)
- [uv](https://docs.astral.sh/uv/), Node.js (React 실습)
- Oracle DB (Todo 앱)

### 설치 & 실행

```bash
git clone https://github.com/HwangSoon96/gg1th_local_llm_basic_ex.git
cd gg1th_local_llm_basic_ex
uv sync

# Ollama 실습
uv run python ollama_basic/1.ollama_test.py

# Todo 앱 → http://localhost:8000
cd todos_app && cp .env_example .env   # DB_USER · DB_PASSWORD · DB_HOST · DB_PORT · DB_SERVICE 입력
uv run python main.py

# React
cd react_basic && npm install && npm run dev
```

Piper 음성 모델은 `3-4.voice_chat_piper.py` 상단 주석의 `wget` 명령으로 `models/piper/`에 다운로드
