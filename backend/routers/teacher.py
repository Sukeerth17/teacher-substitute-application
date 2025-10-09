from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

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
    
    # Check if email is already registered
    db_teacher = db.query(models.Teacher).filter(models.Teacher.email == teacher.email).first()
    if db_teacher:
        raise HTTPException(status_code=400, detail="Email already registered.")
        
    # Create the new teacher instance
    db_teacher = models.Teacher(
        name=teacher.name, 
        email=teacher.email, 
        is_admin=teacher.is_admin
    )
    db.add(db_teacher)
    db.commit()
    db.refresh(db_teacher)
    return db_teacher


@router.get("/{teacher_email}/schedule", response_model=List[schemas.TimetableEntry])
def get_teacher_schedule(teacher_email: str, db: Session = Depends(get_db)):
    """Retrieves the complete current timetable for a specific teacher."""
    
    teacher = db.query(models.Teacher).filter(models.Teacher.email == teacher_email).first()
    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found.")

    schedule = db.query(models.TimetableEntry).filter(
        models.TimetableEntry.teacher_id == teacher.id
    ).order_by(models.TimetableEntry.day_of_week, models.TimetableEntry.start_time).all()
    
    return schedule