from fastapi import FastAPI
import uvicorn # uvicorn은 FastAPI를 실행하기 위한 내장 웹서버

# FastAPI 객체 생성
app = FastAPI()

# http://localhost:8000/ 접속 시 Hello, World! 출력
# http://127.0.0.1:8000/
@app.get("/")
async def root():
    # 비즈니스 로직 처리
    data = "db에서 조회한 데이터 값"
    return {"message": data}

# http://localhost:8000/items
@app.get("/items")
def read_item():
    item_id = 1
    q = "사과"
    return {"item_id": item_id, "q": q}

# http://localhost:8000/items/300?q=소고기
@app.get("/items/{item_id}")
def read_item(item_id: int, q: str | None = None):
# def read_item(item_id, q):
    print(f"item_id: {item_id}, q: {q}")
    return {"item_id": item_id, "q": q}

from pydantic import BaseModel, HttpUrl
from typing import Optional

# DTO
class UserCreate(BaseModel):
    username: str
    password: str
    avatar_url: Optional[HttpUrl] = None
    user_fullname: Optional[str] = None

class UserResponse(BaseModel):
    username: str
    avatar_url: Optional[HttpUrl] = None
    user_fullname: Optional[str] = None

@app.post("/user_info/", response_model=UserResponse)
def create_user(user: UserCreate):
    print(f"username: {user.username}, avatar_url: {user.avatar_url}, user_fullname: {user.user_fullname}")

    user_info = UserResponse(
        username=user.username,
        avatar_url=user.avatar_url,
        user_fullname=user.user_fullname
    )

    return user_info
    # return {"user": user}

@app.post("/user_info/{user_id}")
def create_user(user_id: int, q: str | None = None):
    print(f"user_id: {user_id}, q: {q}")
    return {"user_id": user_id, "q": q}

# uv run fastapi dev
# uv run main.py
if __name__ == "__main__":
    import uvicorn
    # uvicorn.run("현재 파일이름:FastAPI 객체 식별자", reload=True->개발자 모드로 실행)
    uvicorn.run("main:app", reload=True)