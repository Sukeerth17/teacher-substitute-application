from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import date, datetime, time
from typing import List

from database import get_db
import models
import schemas
from utils import send_substitution_notification # Corrected import

# --- Configuration Constants ---
MAX_SUB_WORKLOAD_PER_WEEK = 5 

router = APIRouter(
    prefix="/absence",
    tags=["Daily Operations"],
)

# --- Helper Function: Find Substitute (CORE LOGIC) ---

def find_substitute(
    db: Session, 
    absent_teacher: models.Teacher, 
    absence_day: str, 
    start_time: str, 
    end_time: str, 
    subject: str
) -> models.Teacher | None:
    """
    Finds an available teacher based on priority:
    1. Same subject, under workload limit.
    2. Any teacher, under workload limit.
    """
    
    # 1. Find all potential candidates (teachers NOT the absent one)
    candidates = db.query(models.Teacher).filter(
        models.Teacher.id != absent_teacher.id
    ).all()

    available_candidates: List[models.Teacher] = []
    
    # 2. Filter candidates for availability
    for teacher in candidates:
        # Check if the teacher has any entry in their timetable for this slot
        is_free = db.query(models.TimetableEntry).filter(
            models.TimetableEntry.teacher_id == teacher.id,
            models.TimetableEntry.day_of_week == absence_day,
            models.TimetableEntry.start_time == start_time,
            models.TimetableEntry.end_time == end_time
        ).first() is None
        
        if is_free:
            available_candidates.append(teacher)
    
    if not available_candidates:
        return None # No one is available
        
    # 3. Sort candidates by workload (lowest first)
    available_candidates.sort(key=lambda t: t.sub_workload)
    
    # 4. Apply Priority Logic
    
    # --- Priority 1: Same Subject & Under Workload Limit ---
    same_subject_subs = [
        t for t in available_candidates 
        if t.sub_workload < MAX_SUB_WORKLOAD_PER_WEEK and 
           # Check if the teacher is qualified (has ever taught this subject)
           db.query(models.TimetableEntry).filter(
               models.TimetableEntry.teacher_id == t.id,
               models.TimetableEntry.subject == subject
           ).first() is not None
    ]
    if same_subject_subs:
        # Choose the one with the lowest current workload
        return same_subject_subs[0] 

    # --- Priority 2: Any Available Teacher & Under Workload Limit ---
    any_available_subs = [
        t for t in available_candidates 
        if t.sub_workload < MAX_SUB_WORKLOAD_PER_WEEK
    ]
    if any_available_subs:
        # Choose the one with the lowest current workload
        return any_available_subs[0]

    # 5. Fallback: No one is available under the specified criteria
    return None 

# --- New Simplified Input Schema ---
class SimplifiedAbsenceInput(schemas.BaseModel):
    teacher_name: str
    absence_date: date
    status: str = 'Absent' # Default to Absent
    reason: str | None = None

@router.post("/report-day", status_code=status.HTTP_200_OK)
async def report_full_day_absence(
    data: SimplifiedAbsenceInput, 
    db: Session = Depends(get_db)
):
    """
    Marks a teacher absent/busy for ALL scheduled teaching periods on a given day 
    and auto-assigns substitutes for each period.
    """
    teacher_email = f"{data.teacher_name.lower().replace(' ', '')}@school.edu"

    # 1. Find the Absent Teacher
    absent_teacher = db.query(models.Teacher).filter(
        models.Teacher.email == teacher_email
    ).first()
    
    if not absent_teacher:
        raise HTTPException(status_code=404, detail=f"Teacher '{data.teacher_name}' not found.")

    if data.status == 'Busy' and not data.reason:
        raise HTTPException(status_code=400, detail="Reason is required when status is 'Busy'.")
        
    # 2. Find all scheduled classes for the absent teacher on that day
    absence_weekday = data.absence_date.strftime('%A')
    
    scheduled_classes = db.query(models.TimetableEntry).filter(
        models.TimetableEntry.teacher_id == absent_teacher.id,
        models.TimetableEntry.day_of_week == absence_weekday,
        models.TimetableEntry.is_free == False # Only cover teaching periods
    ).all()
    
    if not scheduled_classes:
        return {"message": f"Teacher {data.teacher_name} has no scheduled teaching periods on {absence_weekday}. No substitution required."}

    substitution_results = []
    
    for class_entry in scheduled_classes:
        # 3. Log the Absence/Busy Status for THIS specific period
        absence_log = models.AbsenceLog(
            absent_teacher_id=absent_teacher.id,
            date=datetime.combine(data.absence_date, time()),
            start_time=class_entry.start_time,
            end_time=class_entry.end_time,
            status=data.status,
            reason=data.reason
        )
        db.add(absence_log)
        db.flush() 

        # 4. Find and Assign Substitute
        substitute = find_substitute(
            db=db,
            absent_teacher=absent_teacher,
            absence_day=absence_weekday,
            start_time=class_entry.start_time,
            end_time=class_entry.end_time,
            subject=class_entry.subject
        )
        
        record = {
            "period": f"{class_entry.start_time}-{class_entry.end_time}",
            "class": class_entry.class_name,
            "subject": class_entry.subject,
            "substitute": "Not Found"
        }
        
        if substitute:
            # 5. Record Substitution History
            substitution_record = models.SubstitutionHistory(
                absence_id=absence_log.id,
                substitute_id=substitute.id,
                class_name=class_entry.class_name,
                subject=class_entry.subject,
                timestamp=datetime.utcnow()
            )
            db.add(substitution_record)

            # 6. Update Substitute Workload
            substitute.sub_workload += 1
            record["substitute"] = substitute.name
            
            # --- 7. Send Email Notification (Final Feature Integration) ---
            notification_details = {
                "date": data.absence_date.strftime('%Y-%m-%d'),
                "day": absence_weekday,
                "period": f"{class_entry.start_time}-{class_entry.end_time}",
                "class_name": class_entry.class_name,
                "subject": class_entry.subject,
                "absent_name": absent_teacher.name,
                "substitute_name": substitute.name,
                "reason": data.reason,
            }
            send_substitution_notification(substitute.email, notification_details)
            
        substitution_results.append(record)

    db.commit()

    return {
        "message": f"Processed {len(scheduled_classes)} periods for {data.teacher_name}. Notifications attempted.",
        "substitutions": substitution_results
    }


@router.get("/workload", response_model=List[schemas.Teacher])
async def get_teacher_workload(db: Session = Depends(get_db)):
    """Retrieves all teachers sorted by current substitution workload."""
    teachers = db.query(models.Teacher).order_by(models.Teacher.sub_workload).all()
    return teachers