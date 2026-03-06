from app.database import engine
from sqlalchemy import text

print("Connecting to database...")
with engine.connect() as conn:
    conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
    conn.commit()
    
print("✅ Vector extension successfully created!")