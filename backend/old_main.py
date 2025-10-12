from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import models
from database import engine, get_db
import traceback

# Create all tables in the database (runs on startup)
models.Base.metadata.create_all(bind=engine)

# Initialize FastAPI app
app = FastAPI(
    title="Teacher Substitution Management System API",
    description="Automates timetable and substitution logic.",
    version="1.0.0",
)

# --- Add CORS Middleware for Frontend ---
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
print("=" * 60)
print("LOADING ROUTERS...")
print("=" * 60)

try:
    from routers import auth
    print("✓ Auth router imported successfully")
    app.include_router(auth.router)
    print("✓ Auth router registered")
except Exception as e:
    print(f"✗ FAILED to load auth router: {e}")
    traceback.print_exc()

try:
    from routers import teacher
    print("✓ Teacher router imported successfully")
    app.include_router(teacher.router)
    print("✓ Teacher router registered")
except Exception as e:
    print(f"✗ FAILED to load teacher router: {e}")
    traceback.print_exc()

try:
    from routers import timetable
    print("✓ Timetable router imported successfully")
    app.include_router(timetable.router)
    print("✓ Timetable router registered")
except Exception as e:
    print(f"✗ FAILED to load timetable router: {e}")
    traceback.print_exc()

try:
    from routers import absence
    print("✓ Absence router imported successfully")
    app.include_router(absence.router)
    print("✓ Absence router registered")
except Exception as e:
    print(f"✗ FAILED to load absence router: {e}")
    traceback.print_exc()

print("=" * 60)
print("ROUTER LOADING COMPLETE")
print("=" * 60)

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
            "error": str(e)
        }

# --- Healthcheck Endpoint ---
@app.get("/health")
def health_check():
    return {"status": "ok"}