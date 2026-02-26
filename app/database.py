from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os
from dotenv import load_dotenv
#from sqlalchemy.exc import OperationalError

load_dotenv()

SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(
    SQLALCHEMY_DATABASE_URL
)

SessionLocal = sessionmaker( autocommit=False, autoflush=False, bind=engine)

# def test_connection():
#     try:
#         with engine.connect() as connection:
#             print("✅ Database connected successfully!")
#     except OperationalError as e:
#         print("❌ Database connection failed!")
#         print(e)

# test_connection()


Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
