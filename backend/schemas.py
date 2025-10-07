from pydantic import BaseModel, EmailStr, Field
from datetime import date, datetime
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
    
    # Configuration for SQLAlchemy ORM compatibility
    model_config = {
        "from_attributes": True
    }

# --- 2. Timetable Schemas (Data from CSV) ---

class TimetableEntryBase(BaseModel):
    """Base schema for a single timetable slot."""
    day_of_week: str
    start_time: str
    end_time: str
    class_name: str
    subject: str
    is_free: bool = False

class TimetableEntry(TimetableEntryBase):
    """Schema for reading a timetable slot from the database."""
    id: int
    teacher_id: int
    
    model_config = {
        "from_attributes": True
    }

# --- 3. Absence/Busy Schemas (Core Logic Input) ---

class AbsenceCreate(BaseModel):
    """Schema for marking a teacher absent or busy (detailed version, used internally)."""
    teacher_email: EmailStr
    absence_date: date
    start_time: str
    end_time: str
    status: str = Field(..., pattern=r"^(Absent|Busy)$")
    reason: Optional[str] = None

# New Simplified Input Schema (Used by /absence/report-day endpoint)
class SimplifiedAbsenceInput(BaseModel):
    """Schema for simplified admin input: only requires name and date."""
    teacher_name: str
    absence_date: date
    status: str = 'Absent'
    reason: str | None = None

class AbsenceLog(BaseModel):
    """Schema for reading an absence log from the database."""
    id: int
    absent_teacher_id: int
    date: date
    status: str
    
    model_config = {
        "from_attributes": True
    }
        
# --- 4. Substitution History Schemas ---

class SubstitutionHistory(BaseModel):
    """Schema for reading substitution history."""
    id: int
    absence_id: int
    substitute_id: int
    class_name: str
    subject: str
    timestamp: datetime
    
    model_config = {
        "from_attributes": True
    }
    
# --- 5. Auth Schemas (JWT) ---

class Token(BaseModel):
    """Schema for the JWT response."""
    access_token: str
    token_type: str

class TokenData(BaseModel):
    """Schema for the data payload inside the JWT."""
    email: str | None = None
    is_admin: bool = False
