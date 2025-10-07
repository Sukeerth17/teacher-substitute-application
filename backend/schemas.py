# backend/schemas.py

from pydantic import BaseModel, EmailStr, Field
from datetime import date
from typing import Optional, List

# --- 1. Teacher Schemas ---

class TeacherBase(BaseModel):
    """Base schema for teacher data (used for creation/update)."""
    name: str = Field(..., min_length=2)
    email: EmailStr
    is_admin: bool = False

class TeacherCreate(TeacherBase):
    """Schema for creating a new teacher."""
    pass

class Teacher(TeacherBase):
    """Schema for reading teacher data (includes DB-generated fields)."""
    id: int
    sub_workload: int
    
    class Config:
        # Pydantic v2 requires model_config
        from_attributes = True

# --- 2. Timetable Schemas ---

class TimetableEntryBase(BaseModel):
    """Base schema for a single timetable slot (used when parsing CSV)."""
    day_of_week: str  # e.g., "Monday"
    start_time: str   # e.g., "08:30"
    end_time: str     # e.g., "09:10"
    class_name: str   # e.g., "2A"
    subject: str      # e.g., "English"
    is_free: bool = False

class TimetableEntry(TimetableEntryBase):
    """Schema for reading a timetable slot from the database."""
    id: int
    teacher_id: int
    
    class Config:
        from_attributes = True

# --- 3. Absence/Busy Schemas ---

class AbsenceCreate(BaseModel):
    """Schema for marking a teacher absent or busy."""
    teacher_email: EmailStr # Identify teacher via email for the API call
    absence_date: date      # The date of absence
    start_time: str
    end_time: str
    status: str = Field(..., pattern=r"^(Absent|Busy)$") # Enforces only 'Absent' or 'Busy'
    reason: Optional[str] = None # Required if status is 'Busy'

class AbsenceLog(AbsenceCreate):
    """Schema for reading an absence log from the database."""
    id: int
    absent_teacher_id: int
    
    class Config:
        from_attributes = True
        
# --- 4. Substitution Schemas ---

class SubstitutionHistory(BaseModel):
    """Schema for reading substitution history."""
    id: int
    absence_id: int
    substitute_id: int
    substitute_name: Optional[str] = None
    class_name: str
    subject: str
    timestamp: date
    
    class Config:
        from_attributes = True