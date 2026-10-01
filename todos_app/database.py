from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
import os
from sqlalchemy import URL

from dotenv import load_dotenv
load_dotenv(override=True)  # .env 파일을 읽어 환경 변수로 등록

##################################
# sqllite3 db 설정
# DB_URL = 'sqlite:///todos.sqlite3'
# # 데이터베이스에 연결하는 엔진을 생성하는 함수
# engine = create_engine(DB_URL, connect_args={'check_same_thread': False})
##################################

# oracle db 설정
# oracle 데이터베이스 URL 설정
# DB_URL = 'oracle+oracledb://joy:1234@localhost:1521/?service_name=FREEPDB1'

# oracle 데이터베이스 URL 설정
DB_URL = URL.create(
    "oracle+oracledb",
    username=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    host=os.getenv("DB_HOST", "localhost"),
    port=int(os.getenv("DB_PORT", "1521")),
    query={"service_name": os.getenv("DB_SERVICE", "FREEPDB1")},
)
# oracle의 경우 check_same_thread 옵션이 필요하지 않음
engine = create_engine(DB_URL, echo=True, future=True)

# 데이터베이스와 상호 작용하는 세션을 생성하는 클래스
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# SQLAlchemy의 선언적 모델링을 위한 기본 클래스
Base = declarative_base()