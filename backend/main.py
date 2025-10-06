# backend/main.py (NEW FILE CONTENT)

from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
# CORRECT ABSOLUTE IMPORTS
import models  
from database import engine, get_db 

# Create all tables in the database (this will run when FastAPI starts)
models.Base.metadata.create_all(bind=engine)

# Initialize FastAPI app
app = FastAPI(
    title="Teacher Substitution Management System API",
    description="Automates timetable and substitution logic.",
    version="1.0.0",
)

# --- Root Endpoint (Test) ---
@app.get("/")
def read_root(db: Session = Depends(get_db)):
    """Simple check to ensure the service is running and connected to DB."""
    # Try to query a teacher to confirm DB connection
    try:
        teacher_count = db.query(models.Teacher).count()
        return {
            "message": "API is running!",
            "db_status": f"Connected, Teachers in DB: {teacher_count}"
        }
    except Exception as e:
        # Note: If the app starts but DB fails, we'll see this error.
        # This means the Python code is running!
        return {
            "message": "API is running, but DB connection failed.",
            "error": str(e)
        }
        
# --- Healthcheck Endpoint ---
@app.get("/health")
def health_check():
    return {"status": "ok"}