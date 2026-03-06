from app.database import engine
from app.models import Base
from sqlalchemy import text

print("Initiating forceful database reset...")

with engine.connect() as conn:
    # 1. Ensure the vector extension is active
    conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
    
    # 2. Forcefully destroy the old tables and ignore constraints
    conn.execute(text("DROP TABLE IF EXISTS messages CASCADE;"))
    conn.execute(text("DROP TABLE IF EXISTS chat_sessions CASCADE;"))
    conn.execute(text("DROP TABLE IF EXISTS users CASCADE;"))
    conn.commit()

print("Old tables destroyed. Rebuilding from scratch...")

# 3. Rebuild fresh tables using the updated models.py (which has the embedding column)
Base.metadata.create_all(bind=engine)

print("✅ Database perfectly rebuilt with the 'embedding' column!")