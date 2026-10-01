import { useState } from 'react'
// import heroImg from './assets/hero.png'
// import reactLogo from './assets/react.svg'
// import viteLogo from './assets/vite.svg'
// import './App.css'
import Header from './components/Header.jsx'
import Greeting from './components/Greeting.jsx'
import Counter from './components/Counter.jsx'
import InputState from './components/InputState.jsx'
import ListRener from './components/ListRender.jsx'
import ConditionalRending from './components/ConditionalRending.jsx'
import UseEffectRender from './components/UseEffectRender.jsx'
import OllamaChat from './components/OllamaChat.jsx'

function App() {
  // const [count, setCount] = useState(0)
  // 자바스크립트 영역
  const title = "헬로 리액트"
  // UseEffectRender 에서 선택한 모델을 App 에서 관리하고 OllamaChat 으로 내려준다.
  const [selectedModel, setSelectedModel] = useState("")
  return (
    <>
      {/* 데이터 렌더링 영역 */}
      <UseEffectRender
        selectedModel={selectedModel}
        onSelectModel={setSelectedModel}
      />
      <OllamaChat model={selectedModel} />
      <ConditionalRending />
      <ListRener />
      <InputState />
      <Counter />
      <Greeting name="joy" age={100} />
      <h1>{title}</h1>
      <Header />
    </>
  )
}

export default App
