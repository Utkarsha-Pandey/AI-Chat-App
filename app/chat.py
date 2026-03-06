from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List
from groq import Groq
from sentence_transformers import SentenceTransformer
from . import models, schemas, config
from .database import get_db
from .auth import get_current_user 

router = APIRouter(
    prefix="/chats",
    tags=["Chats"]
)

# Initialize the Groq Client and the Local Embedding Model
client = Groq(api_key=config.GROQ_API_KEY)
embedder = SentenceTransformer('all-MiniLM-L6-v2')

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
    session = db.query(models.ChatSession).filter(
        models.ChatSession.id == session_id,
        models.ChatSession.user_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")

    # 1. Create vector for user's message
    user_vector = embedder.encode(message_in.content).tolist()

    # 2. Save user message with its vector
    user_message = models.Message(
        session_id=session_id, 
        role=message_in.role, 
        content=message_in.content,
        embedding=user_vector
    )
    db.add(user_message)
    db.commit()

    # 3. Retrieve relevant past memories (Long-Term Memory RAG)
    similar_past_messages = db.query(models.Message).join(models.ChatSession).filter(
        models.ChatSession.user_id == current_user.id,
        models.Message.id != user_message.id 
    ).order_by(
        models.Message.embedding.cosine_distance(user_vector)
    ).limit(3).all()

    retrieved_context = "\n".join([f"- {msg.content}" for msg in similar_past_messages])
    
    system_prompt = f"""You are Nexus, an AI with long-term memory. 
    Here are relevant past memories from this user (if any):
    {retrieved_context}
    
    If the memories are relevant to their new message, use them to answer. Answer clearly and concisely.
    """

    # 4. Fetch recent chat history (Short-Term Memory)
    recent_history = db.query(models.Message).filter(
        models.Message.session_id == session_id
    ).order_by(models.Message.created_at.desc()).limit(5).all()
    recent_history.reverse()

    groq_messages = [{"role": "system", "content": system_prompt}]
    for msg in recent_history:
        groq_messages.append({"role": msg.role, "content": msg.content})

    # 5. Stream the response from Groq
    def iter_groq():
        full_response = ""
        stream = client.chat.completions.create(
            messages=groq_messages,
            model="llama-3.3-70b-versatile",
            temperature=0.3,
            stream=True
        )
        
        for chunk in stream:
            if chunk.choices[0].delta.content:
                text = chunk.choices[0].delta.content
                full_response += text
                yield text
        
        # 6. Save AI's response with its own vector
        from .database import SessionLocal
        db_stream = SessionLocal()
        ai_vector = embedder.encode(full_response).tolist()
        
        ai_message = models.Message(
            session_id=session_id, 
            role="assistant", 
            content=full_response,
            embedding=ai_vector 
        )
        db_stream.add(ai_message)
        db_stream.commit()
        db_stream.close()

    return StreamingResponse(iter_groq(), media_type="text/event-stream")