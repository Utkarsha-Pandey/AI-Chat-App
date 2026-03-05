from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from . import models, schemas
from .database import get_db
from .auth import get_current_user 

router = APIRouter(
    prefix="/chats",
    tags=["Chats"]
)


@router.post("/", response_model=schemas.ChatSessionResponse)
def create_chat_session(
    session_in: schemas.ChatSessionCreate, 
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(get_current_user) # The Guardrail!
):
    new_session = models.ChatSession(
        user_id=current_user.id, 
        title=session_in.title
    )
    db.add(new_session)
    db.commit()
    db.refresh(new_session)
    return new_session

@router.get("/", response_model=List[schemas.ChatSessionResponse])
def get_user_chat_sessions(
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(get_current_user)
):
    sessions = db.query(models.ChatSession).filter(models.ChatSession.user_id == current_user.id).all()
    return sessions

@router.get("/{session_id}/messages", response_model=List[schemas.MessageResponse])
def get_session_messages(
    session_id: int, 
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(get_current_user)
):
    session = db.query(models.ChatSession).filter(
        models.ChatSession.id == session_id,
        models.ChatSession.user_id == current_user.id
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found or unauthorized")

    messages = db.query(models.Message).filter(models.Message.session_id == session_id).all()
    return messages

@router.post("/{session_id}/messages", response_model=schemas.MessageResponse)
def create_message(
    session_id: int, 
    message_in: schemas.MessageCreate, 
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(get_current_user)
):
    session = db.query(models.ChatSession).filter(
        models.ChatSession.id == session_id,
        models.ChatSession.user_id == current_user.id
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found or unauthorized")

    new_message = models.Message(
        session_id=session_id,
        role=message_in.role,
        content=message_in.content
    )
    db.add(new_message)
    db.commit()
    db.refresh(new_message)
    
   

    return new_message