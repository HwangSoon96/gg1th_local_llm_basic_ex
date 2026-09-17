import requests
url = "http://localhost:11434/api/generate"
payload = {
    "model": "qwen3.5:9b",
    # "model": "llama3.2:3b",
    # "model": "llama3.2:latest",
    # "model": "exaone3.5:7.8b",
    "prompt": "로컬 LLM 기반 앱 개발을 배우는 이유를 3문장으로 설명해줘.",
    "stream": False,
}
try:
    response = requests.post(url, json=payload, timeout=120)
    response.raise_for_status()
    data = response.json()
    print("모델 응답:")
    print(data["response"])
except requests.exceptions.ConnectionError:
    print("Ollama 서버에 연결할 수 없습니다. Ollama가 실행 중인지 확인하세요.")
except requests.exceptions.Timeout:
    print("요청 시간이 초과되었습니다. 모델 로딩 또는 PC 성능 문제일 수 있습니다.")
except requests.exceptions.HTTPError as e:
    print(f"HTTP 오류가 발생했습니다: {e}")
except Exception as e:
    print(f"알 수 없는 오류가 발생했습니다: {e}")
