from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
import models
import schemas

router = APIRouter(
    prefix="/teachers",
    tags=["Teacher Management"],
)

@router.post("/", response_model=schemas.Teacher, status_code=status.HTTP_201_CREATED)
def create_teacher(teacher: schemas.TeacherCreate, db: Session = Depends(get_db)):
    """Creates a new teacher account."""
    db_teacher = db.query(models.Teacher).filter(models.Teacher.email == teacher.email).first()
    if db_teacher:
        raise HTTPException(status_code=400, detail="Email already registered.")
        
    db_teacher = models.Teacher(
        name=teacher.name, 
        email=teacher.email, 
        is_admin=teacher.is_admin
    )
    db.add(db_teacher)
    db.commit()
    db.refresh(db_teacher)
    return db_teacher
