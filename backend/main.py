from fastapi import FastAPI, Depends
# CRITICAL: Import CORS middleware for frontend connection
from fastapi.middleware.cors import CORSMiddleware 
from sqlalchemy.orm import Session
import models
# CRITICAL FIX: Import 'engine' directly for database initialization
from database import engine, get_db 

# Create all tables in the database (runs on startup)
models.Base.metadata.create_all(bind=engine)

# Initialize FastAPI app
app = FastAPI(
    title="Teacher Substitution Management System API",
    description="Automates timetable and substitution logic.",
    version="1.0.0",
)

# --- CRITICAL FIX: Add CORS Middleware for Frontend (Port 3000) ---
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# ----------------------------------------


# --- Router Imports and Registration ---
try:
    # Router imports must happen after the app object is created
    from routers import timetable 
    from routers import absence 
    from routers import auth
    from routers import teacher

    app.include_router(timetable.router) 
    app.include_router(absence.router) 
    app.include_router(auth.router)
    app.include_router(teacher.router)
except Exception as e:
    # Log the error but allow the app to start
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
