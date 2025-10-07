from fastapi import APIRouter, Depends, File, HTTPException, status, UploadFile
from sqlalchemy.orm import Session
from fastapi.responses import HTMLResponse # <-- Required for HTML
from io import StringIO
import pandas as pd
from typing import Any
from datetime import time
import re

from database import get_db
import models
import schemas

router = APIRouter(
    prefix="/timetable",
    tags=["Timetable Management"],
)

# --- Helper Functions (No Change) ---

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
    """Placeholder logic to infer Subject from Class Name."""
    class_name = class_name.upper().strip()
    if class_name in ["2A", "2B", "2C", "5B", "5A"]:
        return "English"
    if class_name.startswith("6") or class_name.startswith("3"):
        return "Maths"
    if "DANCE" in class_name or "ART" in class_name:
        return "Co-Curricular"
    if class_name == "READING":
        return "Reading"
    return "Miscellaneous"


# --- NEW: HTML Endpoint for Easy Upload (SIMPLEST VERSION) ---

@router.get("/upload-page", response_class=HTMLResponse)
async def upload_page():
    """Render a simple HTML upload page for easy testing."""
    return """
    <html>
    <head>
      <title>Upload Timetable</title>
      <style>
        body { font-family: 'Inter', sans-serif; padding: 40px; background-color: #f7f7f7; }
        h2 { color: #333; margin-bottom: 20px; }
        form { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); display: flex; gap: 15px; align-items: center; }
        input[type="file"] { padding: 10px; border: 1px solid #ddd; border-radius: 4px; }
        button { background-color: #4f46e5; color: white; padding: 10px 15px; border: none; border-radius: 4px; cursor: pointer; transition: background-color 0.2s; }
        button:hover { background-color: #4338ca; }
      </style>
      <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap" rel="stylesheet">
    </head>
    <body>
      <h2>📘 Upload Master Timetable CSV</h2>
      
      <!-- CRITICAL FIX: Direct POST action without JavaScript -->
      <form action="/timetable/upload-master" enctype="multipart/form-data" method="post">
        <input name="file" type="file" accept=".csv" required>
        <button type="submit">Upload & Process</button>
      </form>
      
    </body>
    </html>
    """

# --- API Endpoint: Upload Master Timetable CSV (FINAL ROBUST LOGIC) ---

@router.post("/upload-master", status_code=status.HTTP_201_CREATED)
async def upload_master_timetable(
    file: UploadFile = File(...), 
    db: Session = Depends(get_db)
):
    
    if not getattr(file, "filename", "").endswith(".csv"):
        raise HTTPException(status_code=400, detail="Invalid file provided. Please upload a CSV file.")
    
    try:
        content = await file.read()
        content_str = content.decode("utf-8")
        
        # 1. Read the CSV: Read without headers initially to find the exact rows
        df_raw = pd.read_csv(StringIO(content_str), header=None, skip_blank_lines=True)
        
        # 2. Identify header row indices
        time_slot_row_index = None
        for i, row in df_raw.iterrows():
            if row.astype(str).str.contains(r'\d{2}:\d{2} - \d{2}:\d{2}').any():
                time_slot_row_index = i
                break
        
        if time_slot_row_index is None or time_slot_row_index < 3:
            raise ValueError("CSV structure error: Could not find time slots or header rows.")

        day_header_row_index = time_slot_row_index - 1
        teacher_header_row_index = time_slot_row_index - 2 

        # 3. Extract and Clean Headers
        # CRITICAL FIX: Convert to string immediately after fillna to prevent 'numpy.float64' errors
        teacher_names = df_raw.iloc[teacher_header_row_index].fillna(method='ffill').astype(str)
        day_names = df_raw.iloc[day_header_row_index].astype(str)
        
        # Clean Teacher Name (Remove HRT/NON-HRT, numbers, and excess spaces)
        # The apply function is now safe because the input 'x' is guaranteed to be a string
        clean_teachers = teacher_names.apply(lambda x: re.sub(r'\(.*?\)|HRT -?|NON-HRT| \(\d+\)', '', x).strip().split(',')[0].strip())
        
        # 4. Create Combined Header List (e.g., NAGARATHNA_Monday)
        combined_headers = []
        for i in range(1, len(df_raw.columns)): # Start from column 1 (skip Time column)
            teacher_name = clean_teachers.iloc[i].strip()
            day_name = day_names.iloc[i].strip()
            # Only include columns that have a valid teacher and day name
            if teacher_name and day_name:
                combined_headers.append(f"{teacher_name}_{day_name}")
            else:
                combined_headers.append(f"SKIP_COL_{i}") # Placeholder for invalid columns
        
        # 5. Prepare Data Block for Melting
        df = df_raw.iloc[time_slot_row_index:].copy()
        
        # Set the cleaned headers to the data block (TimeSlot + combined headers)
        df.columns = ['TimeSlot'] + combined_headers
        
        # 6. Melt the DataFrame from wide to long format
        df_long = df.melt(
            id_vars=['TimeSlot'],
            var_name='teacher_day', 
            value_name='class_name'
        )
        
        # 7. Clean and filter data
        df_long = df_long[~df_long['teacher_day'].str.contains('SKIP_COL', case=False, na=False)] # Remove skipped columns
        df_long.dropna(subset=['class_name'], inplace=True)
        # CRITICAL FIX: Convert class_name to string before filtering/stripping the data column
        df_long['class_name'] = df_long['class_name'].astype(str) 
        df_long = df_long[~df_long['class_name'].str.contains('BREAK|LUNCH|HRT|NON-HRT', case=False, na=False)]
        df_long['class_name'] = df_long['class_name'].str.strip()
        
        # Split the 'teacher_day' column
        df_long[['teacher_name', 'day_of_week']] = df_long['teacher_day'].str.split('_', expand=True)

        # 8. Database Processing
        total_entries = 0
        db.query(models.TimetableEntry).delete(synchronize_session=False)

        for teacher_name, group_df in df_long.groupby('teacher_name'):
            if not teacher_name or teacher_name.strip() == 'nan': continue

            # --- Teacher Creation/Update ---
            teacher_email = f"{teacher_name.lower().replace(' ', '')}@school.edu"
            teacher = db.query(models.Teacher).filter(models.Teacher.email == teacher_email).first()
            if not teacher:
                teacher = models.Teacher(name=teacher_name, email=teacher_email, is_admin=False)
                db.add(teacher)
                db.flush() 
            
            # --- Timetable Insertion ---
            new_entries = []
            for _, row in group_df.iterrows():
                time_slot = str(row['TimeSlot']).split('-')
                if len(time_slot) != 2: continue
    
                start_time_str = time_slot[0].strip()
                end_time_str = time_slot[1].strip()
                class_name = row['class_name']
                
                subject = get_subject_from_class(class_name)
                is_free = (class_name.upper() == "READING")
                
                entry = models.TimetableEntry(
                    teacher_id=teacher.id,
                    day_of_week=row['day_of_week'].strip(),
                    start_time=start_time_str,
                    end_time=end_time_str,
                    class_name=class_name,
                    subject=subject,
                    is_free=is_free
                )
                new_entries.append(entry)
                total_entries += 1

            db.add_all(new_entries)
        
        db.commit()

        return {"message": f"Master timetable uploaded and replaced successfully for {len(df_long['teacher_name'].unique())} teachers.", 
                "total_entries": total_entries}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to process timetable. Error: {type(e).__name__}: {str(e)}")
