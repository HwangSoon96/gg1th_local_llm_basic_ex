from fastapi import FastAPI

# FastAPI 객체 생성
app = FastAPI()

# http://localhost:8000/ 접속 시 Hello, World! 출력
# http://127.0.0.1:8000/
@app.get("/")
async def root():
    # 비즈니스 로직 처리
    data = "db에서 조회한 데이터 값"
    return {"message": data}

@app.get("/items")
def read_item():
    item_id = 1
    q = "사과"
    return {"item_id": item_id, "q": q}

@app.get("/items/{item_id}")
def read_item(item_id: int, q: str | None = None):
    return {"item_id": item_id, "q": q}