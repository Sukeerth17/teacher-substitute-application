# backend/routers/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from jose import JWTError, jwt
import os

from database import get_db
import models
from schemas import Token, TokenData

# Load settings from .env
SECRET_KEY = os.getenv("SECRET_KEY", "default-secret")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))
AUTHORIZED_DOMAIN = os.getenv("AUTHORIZED_DOMAIN", "school.edu")

router = APIRouter(
    tags=["Authentication"],
)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# --- JWT Functions (Normally in a separate utility file) ---

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def authenticate_google_user(email: str, db: Session) -> models.Teacher | None:
    # 1. Domain Check
    if not email.endswith(f"@{AUTHORIZED_DOMAIN}"):
        return None # Domain unauthorized
    
    # 2. Find/Create Teacher
    teacher = db.query(models.Teacher).filter(models.Teacher.email == email).first()
    if not teacher:
        # For simplicity, we auto-create the teacher record upon first successful domain login
        name = email.split('@')[0].capitalize()
        teacher = models.Teacher(email=email, name=name, is_admin=False)
        db.add(teacher)
        db.commit()
        db.refresh(teacher)
    
    return teacher

# --- Endpoint Definitions ---

# NOTE: This token endpoint is just a placeholder, as Google OAuth requires a redirect flow.
# We simulate a successful Google callback.
@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), 
    db: Session = Depends(get_db)
):
    # In a real app, form_data.username would be the ID Token from Google
    email = form_data.username # Use 'username' field to pass the authenticated email
    
    # Placeholder: Validate that the provided email is from an authorized domain
    user = authenticate_google_user(email, db)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized email domain or user not found.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create the JWT
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email, "is_admin": user.is_admin}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

# --- Dependency to Get Current User ---
async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        is_admin: bool = payload.get("is_admin")
        if email is None:
            raise credentials_exception
        token_data = TokenData(email=email, is_admin=is_admin)
    except JWTError:
        raise credentials_exception
    
    user = db.query(models.Teacher).filter(models.Teacher.email == token_data.email).first()
    if user is None:
        raise credentials_exception
    return user

# --- Admin Access Control Dependency ---
async def get_current_admin(current_user: models.Teacher = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Operation requires administrative privileges."
        )
    return current_user

# Example of protecting an endpoint (e.g., timetable upload)
# @router.post("/protected", dependencies=[Depends(get_current_admin)])
# async def protected_endpoint(): return {"message": "Admin access granted"}