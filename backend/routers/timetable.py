from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, status
from sqlalchemy.orm import Session
from io import StringIO
import pandas as pd
from datetime import time
# CRITICAL FIX: Explicitly import File from fastapi

from database import get_db
import models
import schemas

# Create a FastAPI router instance for timetable endpoints
router = APIRouter(
    prefix="/timetable",
    tags=["Timetable Management"],
)

# --- Helper Functions ---

def parse_time_str(time_str: str) -> time:
    """Safely converts string time (HH:MM) to datetime.time."""
    try:
        hour, minute = map(int, time_str.split(':'))
        return time(hour, minute)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Time format error: '{time_str}'. Must be HH:MM."
        )

def get_subject_from_class(class_name: str) -> str:
    """
    Placeholder logic to infer Subject from Class Name (like '2A' or '6B').
    """
    class_name = class_name.upper().strip()
    if class_name in ["2A", "2B", "2C"]:
        return "English"
    if class_name.startswith("6"):
        return "Maths"
    if class_name == "READING":
        return "Reading"
    return "Miscellaneous" # Default subject


# --- API Endpoint: Upload Master Timetable CSV ---

@router.post("/upload-master", status_code=status.HTTP_201_CREATED)
async def upload_master_timetable(
    # FIX: 'File' is now properly defined. 
    # Using 'Any' = File(...) to bypass Mac/Docker environment bug 
    file: UploadFile = File(...), 
    db: Session = Depends(get_db)
):
    """
    Uploads the master timetable CSV, parses it, and replaces all existing timetable data.
    """
    # CRITICAL: Re-import UploadFile locally for validation and use
    from fastapi import UploadFile 

    print("Received file:", getattr(file, "filename", None))
    
    if not getattr(file, "filename", "").endswith(".csv"):
     raise HTTPException(status_code=400, detail="Invalid file provided. Please upload a CSV file.")


    
    try:
        # 1. Read the file content
        content = await file.read()
        content_str = content.decode("utf-8")
        
        # 2. Use pandas to read the wide-format CSV
        df = pd.read_csv(StringIO(content_str))

        # --- Identify Teacher and Melt Data ---
        
        teacher_name = "NITHYA" 
        teacher_email = "nithya@school.edu"
        
        time_column = df.columns[0]
        
        df_long = df.melt(
            id_vars=[time_column], 
            value_vars=df.columns[1:],
            var_name='day_of_week', 
            value_name='class_name'
        )
        
        # Clean up: remove empty cells, BREAK/LUNCH periods
        df_long.dropna(subset=['class_name'], inplace=True)
        df_long = df_long[~df_long['class_name'].str.contains('BREAK|LUNCH', case=False, na=False)]
        df_long['class_name'] = df_long['class_name'].str.strip()
        
        # --- Teacher and Timetable Entry Creation ---
        
        # 3. Create or get the teacher (Teacher email should be unique)
        teacher = db.query(models.Teacher).filter(models.Teacher.email == teacher_email).first()
        if not teacher:
            teacher = models.Teacher(name=teacher_name, email=teacher_email, is_admin=False)
            db.add(teacher)
            db.flush() 
        
        teacher_id = teacher.id

        # 4. CRITICAL: Clear existing timetable for this teacher (The "Update" requirement)
        db.query(models.TimetableEntry).filter(models.TimetableEntry.teacher_id == teacher_id).delete(synchronize_session=False)

        # 5. Process and insert new entries
        new_entries = []
        for _, row in df_long.iterrows():
            time_slot = str(row[time_column]).split('-')
            
            if len(time_slot) != 2: continue

            start_time_str = time_slot[0].strip()
            end_time_str = time_slot[1].strip()
            class_name = row['class_name']
            
            subject = get_subject_from_class(class_name)
            is_free = (class_name.upper() == "READING")
            
            # Create a new timetable entry model instance
            entry = models.TimetableEntry(
                teacher_id=teacher_id,
                day_of_week=row['day_of_week'].strip(),
                start_time=start_time_str,
                end_time=end_time_str,
                class_name=class_name,
                subject=subject,
                is_free=is_free
            )
            new_entries.append(entry)

        db.add_all(new_entries)
        db.commit()

        return {"message": f"Master timetable uploaded and replaced successfully for {teacher_name}.", 
                "total_entries": len(new_entries)}

    except Exception as e:
        db.rollback()
        # Raise an internal server error detailing the failure
        raise HTTPException(status_code=500, detail=f"Failed to process timetable: {type(e).__name__}: {str(e)}")