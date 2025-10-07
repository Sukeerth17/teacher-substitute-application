from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
# Absolute imports for local files
import models
from database import engine, get_db
# Import the timetable router
from routers import timetable 

# Create all tables in the database (runs on startup)
models.Base.metadata.create_all(bind=engine)

# Initialize FastAPI app
app = FastAPI(
    title="Teacher Substitution Management System API",
    description="Automates timetable and substitution logic.",
    version="1.0.0",
)

# Register the API routers
app.include_router(timetable.router) 

# --- Root Endpoint (Test & DB Status) ---
@app.get("/")
def read_root(db: Session = Depends(get_db)):
    """Simple check to ensure the service is running and connected to DB."""
    # Try to query a teacher to confirm DB connection
    try:
        # Check if the Teacher table exists and can be queried
        teacher_count = db.query(models.Teacher).count()
        return {
            "message": "Teacher Substitution API is running!",
            "db_status": f"Connected successfully. Teacher count: {teacher_count}"
        }
    except Exception as e:
        # Catch connection failure if the DB is still initializing
        return {
            "message": "API is running, but DB connection failed.",
            "error": "Database error (check DB service logs)."
        }
        
# --- Healthcheck Endpoint ---
@app.get("/health")
def health_check():
    return {"status": "ok"}