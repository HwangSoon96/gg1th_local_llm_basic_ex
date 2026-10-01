from sqlalchemy import Column, Integer, Boolean, Text, String, Identity
from database import Base

# sqlite 테이블 클래스로 정의
# class Todo(Base):
#     __tablename__ = 'todos'
#     id = Column(Integer, primary_key=True)
#     task = Column(Text)
#     completed = Column(Boolean, default=False)

# oracle 테이블 클래스로 정의
class Todo(Base):
    __tablename__ = 'todos'
    id = Column(Integer, Identity(), primary_key=True)
    task = Column(String(300))
    completed = Column(Boolean, default=False)