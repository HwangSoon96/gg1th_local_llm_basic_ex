import { useState } from "react";

function ListRender() {
    const messages = [
        { id: 1, role: "user", content: "안녕하세요." },
        { id: 2, role: "assistant", content: "무엇을 도와드릴까요?" },
        { id: 3, role: "user2", content: "안녕히 가세요." },
        { id: 4, role: "assistant2", content: "잘가." },
    ];
    // 선택된 메시지의 id 를 상태로 관리한다. (선택 안 됨: null)
    const [selectedId, setSelectedId] = useState(null);
    return (
        <main>
            <h1>메시지 목록</h1>
            {messages.map((message) => (
                <div
                    key={message.id}
                    onClick={() => setSelectedId(message.id)}
                    style={{
                        cursor: "pointer",
                        padding: "8px",
                        borderRadius: "6px",
                        // 선택된 항목이면 배경색으로 강조한다.
                        backgroundColor:
                            selectedId === message.id ? "#d0ebff" : "transparent",
                    }}
                >
                    <strong>{message.role}</strong>
                    <p>{message.content}</p>
                </div>
            ))}
        </main>
    );
}
export default ListRender;
