from fastapi import FastAPI, Form, Request, Depends, status
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from database import engine, SessionLocal, Base
from sqlalchemy.orm import Session
import os
import uvicorn
import models

# models에 정의한 모든 클래스, 연결한 DB엔진에 테이블로 생성
Base.metadata.create_all(bind=engine)

# FastAPI() 객체 생성
app = FastAPI()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        # 마지막에 무조건 닫음
        db.close()

abs_path = os.path.dirname(os.path.realpath(__file__))

# 템플릿 디렉토리 식별 객체 변수
templates = Jinja2Templates(directory=f"{abs_path}/templates")

# 정적 파일 디렉토리 식별 객체 변수
app.mount("/static", StaticFiles(directory=f"{abs_path}/static"), name="static")

@app.get("/")
def home(request: Request,
         db_ss: Session = Depends(get_db)
         ):
    # 테이블 조회
    todos_list = db_ss.query(models.Todo).order_by(models.Todo.id.desc()).all()
    # print(f"todos_list: {todos_list}")
    # for todo in todos_list:
    #     print(f"todo: {todo.id}, {todo.task}, {todo.completed}")

    return templates.TemplateResponse(
        request = request,
        name = "index.html",
        context={ "todos":  todos_list}
    )

# todo 데이터를 받아서 db 테이블에 저장하기
# http://127.0.0.1:8000/add
@app.post("/add")
def add(request: Request, 
        task: str = Form(...),
        db_ss: SessionLocal = Depends(get_db)
        ):
    print(f"task: {task}")
    todo = models.Todo(task=task) # task 데이터 받기
    db_ss.add(todo) 
    db_ss.commit() # db 테이블에 저장

    return RedirectResponse(url=app.url_path_for("home"), # home으로 redirect
                            status_code=status.HTTP_303_SEE_OTHER) 

@app.get("/edit/{todo_id}") # 수정할 레코드 조회
def edit_form(todo_id: int,
         request: Request,
         db_ss: SessionLocal = Depends(get_db)
         ):
    todo = db_ss.query(models.Todo).filter(models.Todo.id == todo_id).first()

    # 예외처리
    if todo is None:
        return RedirectResponse(url=app.url_path_for("home"), # home으로 redirect
                            status_code=status.HTTP_303_SEE_OTHER)

    print(f"todo: {todo.task}")

    # 페이지 아래쪽 목록용 — home과 같은 정렬 사용
    todos_list = db_ss.query(models.Todo).order_by(models.Todo.id.desc()).all()

    return templates.TemplateResponse(
        request = request,
        name = "edit.html",
        context={ "todo":  todo, "todos": todos_list}
    )

@app.post("/edit/{todo_id}") # 수정 내용 반영
def edit(todo_id: int,
         request: Request,
         task: str = Form(...),
         completed: bool = Form(False),
         db_ss: SessionLocal = Depends(get_db)
         ):
    todo = db_ss.query(models.Todo).filter(models.Todo.id == todo_id).first()
    todo.task = task
    todo.completed = completed
    db_ss.commit() # db 테이블에 저장
    return RedirectResponse(url=app.url_path_for("home"), # home으로 redirect
                            status_code=status.HTTP_303_SEE_OTHER)

@app.post("/delete/{todo_id}") # 레코드 삭제
def delete(todo_id: int,
         request: Request,
         db_ss: SessionLocal = Depends(get_db)
         ):
    todo = db_ss.query(models.Todo).filter(models.Todo.id == todo_id).first()
    db_ss.delete(todo)
    db_ss.commit() # db 테이블에 저장
    return RedirectResponse(url=app.url_path_for("home"), # home으로 redirect
                            status_code=status.HTTP_303_SEE_OTHER)

if __name__ == "__main__":
    # uvicorn.run("현재 파일이름:FastAPI 객체 식별자", reload=True->개발자 모드로 실행)
    uvicorn.run("main:app", reload=True)