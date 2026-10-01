function ConditionalRending() {
  const isLoading = false;
  return (
    <main>
      <h1>조건부 렌더링</h1>
      {isLoading ? <p>응답 생성 중입니다...</p> : <p>응답이 완료되었습니다.</p>}
    </main>
  );
}
export default ConditionalRending;
