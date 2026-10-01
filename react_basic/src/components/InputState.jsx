import { useState } from 'react'

function InputState() {
    const [message, setMessage] = useState('')
    return (
        <main>
            <h1>입력값 상태 관리 예제</h1>
            <input type="text" value={message}
                onChange={(e) => setMessage(e.target.value)}
                placeholder="메세지를 입력하세요"
            />
            <p>입력한 메세지 : {message}</p>
        </main>
    )
}

export default InputState