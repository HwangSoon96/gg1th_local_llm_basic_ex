import { useEffect, useState } from "react";
function UseEffectRender({ selectedModel, onSelectModel }) {
  const [models, setModels] = useState([]);
  const URL = "http://localhost:8000/models";
  useEffect(() => {
    fetch(URL)
      .then((response) => response.json())
      .then((data) => setModels(data.models || []))
      .catch((error) => console.error(error));
  }, []); // [] 처음 실행될 때 한번만 실행하도록 함
  return (
    <main>
      <h1>모델 목록</h1>
      {/* 선택 값과 변경 처리는 부모(App)에서 내려준 props 로 처리한다. */}
      <select
        value={selectedModel}
        onChange={(event) => onSelectModel(event.target.value)}
      >
        <option value="">모델을 선택하세요.</option>
        {models.map((model) => (
          <option key={model} value={model}>
            {model}
          </option>
        ))}
      </select>
    </main>
  );
}
export default UseEffectRender;
