# backend/models.py (NEW FILE CONTENT)

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Float
from sqlalchemy.orm import relationship
from database import Base # <-- THE CRITICAL FIX: ABSOLUTE IMPORT
from datetime import datetime

# --- 1. Teacher Model ---
class Teacher(Base):
    """Stores basic teacher information and their current substitution workload."""
    __tablename__ = "teachers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    email = Column(String, unique=True, index=True)
    # Total substitution periods assigned over a rolling period (e.g., current week/month)
    sub_workload = Column(Integer, default=0)
    is_admin = Column(Boolean, default=False)
    
    # Relationships
    timetable_entries = relationship("TimetableEntry", back_populates="teacher")
    absences = relationship("AbsenceLog", back_populates="absent_teacher")
    substitutions = relationship("SubstitutionHistory", back_populates="substitute_teacher", foreign_keys='[SubstitutionHistory.substitute_id]')


# --- 2. Timetable Entry Model ---
class TimetableEntry(Base):
    """The master timetable data, loaded from the CSV (the configuration file)."""
    __tablename__ = "timetable"

    id = Column(Integer, primary_key=True, index=True)
    teacher_id = Column(Integer, ForeignKey("teachers.id"))
    day_of_week = Column(String)  # e.g., "Monday"
    start_time = Column(String)   # e.g., "08:30"
    end_time = Column(String)     # e.g., "09:10"
    class_name = Column(String)   # e.g., "2A"
    subject = Column(String)      # Explicit Subject (e.g., "Maths") - normalized from CSV if possible
    is_free = Column(Boolean, default=False) # True for non-teaching periods (like 'Reading', or free periods)

    # Relationship
    teacher = relationship("Teacher", back_populates="timetable_entries")


# --- 3. Absence/Busy Log Model ---
class AbsenceLog(Base):
    """Logs when a teacher is marked absent or busy."""
    __tablename__ = "absence_log"

    id = Column(Integer, primary_key=True, index=True)
    absent_teacher_id = Column(Integer, ForeignKey("teachers.id"))
    date = Column(DateTime)
    start_time = Column(String)
    end_time = Column(String)
    status = Column(String)  # 'Absent' or 'Busy'
    reason = Column(String, nullable=True) # Required for 'Busy' status
    
    # Relationship
    absent_teacher = relationship("Teacher", back_populates="absences")
    substitution_record = relationship("SubstitutionHistory", back_populates="absence_record", uselist=False)


# --- 4. Substitution History Model ---
class SubstitutionHistory(Base):
    """Records the final substitution assignment and details."""
    __tablename__ = "substitution_history"

    id = Column(Integer, primary_key=True, index=True)
    absence_id = Column(Integer, ForeignKey("absence_log.id"))
    substitute_id = Column(Integer, ForeignKey("teachers.id"))
    class_name = Column(String)
    subject = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    absence_record = relationship("AbsenceLog", back_populates="substitution_record")
    substitute_teacher = relationship("Teacher", back_populates="substitutions", foreign_keys=[substitute_id])