import { useState } from "react";
import axios from "axios";

const CHAT_URL = "http://localhost:8000/chat";

// UseEffectRender 에서 선택한 모델을 App 을 통해 props(model)로 받는다.
function OllamaChat({ model }) {
  // 입력값, 응답 결과, 로딩 상태, 오류 메시지를 상태로 관리한다.
  const [message, setMessage] = useState("");
  const [answer, setAnswer] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const handleSend = async () => {
    if (!message.trim()) {
      alert("메시지를 입력하세요.");
      return;
    }
    // 상단 모델 목록에서 모델을 먼저 선택해야 한다.
    if (!model) {
      alert("모델을 선택하세요.");
      return;
    }
    // 요청 전 상태 초기화
    setIsLoading(true);
    setErrorMessage("");
    setAnswer(null);
    try {
      // FastAPI 백엔드의 /chat API 로 사용자 메시지를 전송한다.
      const response = await axios.post(CHAT_URL, {
        message: message,
        // model: "exaone3.5:7.8b",
        model: model, // UseEffectRender 에서 선택해 props 로 내려온 모델
        system_prompt: "너는 초보자를 돕는 AI 강사다.",
        temperature: 0.7,
        top_p: 0.9,
        num_predict: 256,
      });
      // 응답 전체 객체를 상태에 저장한다.
      const data = response.data;
      console.log(data);
      setAnswer(data);
    } catch (error) {
      console.error(error);
      setErrorMessage("서버 요청 중 오류가 발생했습니다.");
    } finally {
      setIsLoading(false);
    }
  };
  return (
    <main className="app">
      <h1>Ollama Chat</h1>
      <section>
        <textarea
          value={message}
          onChange={(event) => setMessage(event.target.value)}
          placeholder="메시지를 입력하세요."
          rows={5}
        />
        <br />
        <button onClick={handleSend} disabled={isLoading}>
          {isLoading ? "응답 생성 중..." : "전송"}
        </button>
      </section>
      <section>
        <h2>응답</h2>
        {errorMessage && <p style={{ color: "red" }}>{errorMessage}</p>}
        {/* 로딩 중이면 안내 문구를 보여주고, 응답이 있으면 결과를 출력한다. */}
        {isLoading ? (
          <p>Ollama 가 응답을 생성하고 있습니다.</p>
        ) : (
          answer && (
            <>
              <p>{answer.model}</p>
              <p>{answer.message}</p>
              <p>{answer.elapsed_time}</p>
            </>
          )
        )}
      </section>
    </main>
  );
}

export default OllamaChat;
