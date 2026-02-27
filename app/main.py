from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from . import models
from .database import engine, get_db

models.Base.metadata.create_all(bind=engine)

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": " Welcome, Utkarsha."}

@app.post("/test-user/")
def create_test_user(email: str, password: str, db: Session = Depends(get_db)):
    new_user = models.User(email=email, hashed_password=password) 
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return new_user