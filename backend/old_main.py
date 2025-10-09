from fastapi import FastAPI, Depends
# NEW IMPORT: Add the CORS middleware
from fastapi.middleware.cors import CORSMiddleware 
from sqlalchemy.orm import Session
import models
from database import engine, get_db 
# Create all tables in the database (runs on startup)
models.Base.metadata.create_all(bind=get_db().__self__.bind)
models.Base.metadata.create_all(bind=engine)

# Initialize FastAPI app
app = FastAPI(
    title="Teacher Substitution Management System API",
    description="Automates timetable and substitution logic.",
    version="1.0.0",
)

# --- CRITICAL FIX: Add CORS Middleware ---
# Define the origins that are allowed to make requests (your frontend running on port 3000)
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"], # Allow all HTTP methods (POST, GET, etc.)
    allow_headers=["*"], # Allow all headers (including Authorization)
)
# ----------------------------------------


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