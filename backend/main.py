# backend/main.py (FINAL STRUCTURE FIX)
from routers import auth
from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
import models
from database import engine, get_db

# Create all tables in the database (runs on startup)
models.Base.metadata.create_all(bind=engine)

# Initialize FastAPI app (CRITICAL: MUST BE DEFINED FIRST)
app = FastAPI(
    title="Teacher Substitution Management System API",
    description="Automates timetable and substitution logic.",
    version="1.0.0",
)

# --- Router Imports and Registration (Must happen AFTER app is defined) ---
try:
    from routers import timetable 
    from routers import absence 
    from routers import auth
    from routers import teacher

    app.include_router(timetable.router) 
    app.include_router(absence.router) 
    app.include_router(auth.router)
    app.include_router(teacher.router)
except Exception as e:
    # Log the error but allow the app to start so we can diagnose it
    print(f"CRITICAL ROUTER LOAD FAILURE: {e}")


# --- Root Endpoint (Test & DB Status) ---
@app.get("/")
def read_root(db: Session = Depends(get_db)):
    """Simple check to ensure the service is running and connected to DB."""
    try:
        teacher_count = db.query(models.Teacher).count()
        return {
            "message": "Teacher Substitution API is running!",
            "db_status": f"Connected successfully. Teacher count: {teacher_count}"
        }
    except Exception as e:
        return {
            "message": "API is running, but DB connection failed.",
            "error": "Database error (check DB service logs)."
        }
        
# --- Healthcheck Endpoint ---
@app.get("/health")
def health_check():
    return {"status": "ok"}