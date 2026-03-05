from fastapi import APIRouter, Depends, HTTPException, status
from httpcore import stream
from httpx import stream
from sqlalchemy.orm import Session
from typing import List
from groq import Groq
from . import models, schemas, config
from .database import get_db
from .auth import get_current_user 
from fastapi.responses import StreamingResponse

router = APIRouter(
    prefix="/chats",
    tags=["Chats"]
)

# Initialize the Groq Client
client = Groq(api_key=config.GROQ_API_KEY)

@router.post("/", response_model=schemas.ChatSessionResponse)
def create_chat_session(
    session_in: schemas.ChatSessionCreate, 
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(get_current_user)
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


@router.post("/{session_id}/messages/stream")
def stream_message(
    session_id: int, 
    message_in: schemas.MessageCreate, 
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(get_current_user)
):
    # 1. Verify session
    session = db.query(models.ChatSession).filter(
        models.ChatSession.id == session_id,
        models.ChatSession.user_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")

    # 2. Save User Message
    user_message = models.Message(
        session_id=session_id, 
        role=message_in.role, 
        content=message_in.content
    )
    db.add(user_message)
    db.commit()

    # 3. Get History
    history = db.query(models.Message).filter(
        models.Message.session_id == session_id
    ).order_by(models.Message.created_at.asc()).limit(10).all()
    
    groq_messages = [{"role": "system", "content": "You are Nexus, a helpful assistant."}]
    for msg in history:
        groq_messages.append({"role": msg.role, "content": msg.content})

    # 4. Define the generator function INSIDE the route
    def iter_groq():
        full_response = ""
        stream = client.chat.completions.create(
            messages=groq_messages,
            model="llama-3.3-70b-versatile",
            temperature=0.3,
            stream=True # Enable Streaming!
        )
        
        for chunk in stream:
            if chunk.choices[0].delta.content:
                text = chunk.choices[0].delta.content
                full_response += text
                yield text
        
        # 5. Save AI Response to DB after streaming is done
        from .database import SessionLocal
        db_stream = SessionLocal()
        ai_message = models.Message(
            session_id=session_id, 
            role="assistant", 
            content=full_response
        )
        db_stream.add(ai_message)
        db_stream.commit()
        db_stream.close()

    return StreamingResponse(iter_groq(), media_type="text/event-stream")