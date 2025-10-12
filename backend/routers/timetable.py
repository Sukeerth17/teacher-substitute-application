from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from sqlalchemy.orm import Session
from fastapi.responses import HTMLResponse
from io import BytesIO, StringIO
import pandas as pd
import re
from typing import Any, Dict, List
from database import get_db
import models
import schemas
from datetime import time

router = APIRouter(
    prefix="/timetable",
    tags=["Timetable Management"],
)

# --- Helper Functions ---
def parse_subject_mapping(df_raw: pd.DataFrame) -> Dict[str, str]:
    """
    Parses the subject mapping section from the CSV.
    Returns a dictionary mapping teacher names to their subjects.
    """
    subject_mapping = {}
    current_subject = None
    
    for row_idx in range(len(df_raw)):
        for col_idx in range(len(df_raw.columns)):
            cell_value = str(df_raw.iloc[row_idx, col_idx]).strip()
            
            if not cell_value or cell_value == 'nan':
                continue
            
            if cell_value in ["English", "Maths", "Mathematics", "Science", "Social Studies", 
                            "Hindi", "Co-Curricular", "Reading", "Art", "Music", "Dance",
                            "Physical Education", "Computer Science", "EVS"]:
                current_subject = cell_value
            elif current_subject:
                teacher_name = cell_value.strip()
                if teacher_name and not any(day in teacher_name for day in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']):
                    subject_mapping[teacher_name] = current_subject
    
    return subject_mapping

def get_subject_from_mapping_or_class(teacher_name: str, class_name: str, subject_mapping: Dict[str, str]) -> str:
    """First checks if teacher has a subject mapping, otherwise infers from class name."""
    if teacher_name in subject_mapping:
        return subject_mapping[teacher_name]
    
    class_name = class_name.upper().strip()
    clean_class = re.sub(r'\([^)]*\)', '', class_name).strip()
    
    if any(x in class_name for x in ["DANCE", "DAN", "ART", "MUSIC", "BAND", "CACA", "PE", "PHYSICAL"]):
        return "Co-Curricular"
    
    if class_name == "READING" or "LIBRARY" in class_name:
        return "Reading"
    
    if clean_class in ["2A", "2B", "2C", "5B", "5A"]:
        return "English"
    if clean_class.startswith("6") or clean_class.startswith("3") or clean_class.startswith("4"):
        return "Maths"
    
    return "Miscellaneous"

def is_teacher_name_cell(cell_value: str) -> bool:
    """Determines if a cell contains a teacher name."""
    cell_value = str(cell_value).strip()
    
    if not cell_value or cell_value == 'nan':
        return False
    
    if re.search(r'HRT\s*-?\s*\d+[A-Z]', cell_value):
        return False
    
    if 'NON-HRT' in cell_value:
        return False
    
    if cell_value in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']:
        return False
    
    if re.search(r'\d{1,2}:\d{2}', cell_value):
        return False
    
    if re.match(r'^[\d]+[A-Z](/[A-Z])?\s*\(.*\)$', cell_value):
        return False
    
    single_word_rejects = [
        'READING', 'ART', 'MUSIC', 'DANCE', 'KARATE', 'YOGA', 'SPORTS',
        'PE', 'LIBRARY', 'CRAFT', 'DRAMA', 'THEATER', 'BAND', 'CHOIR'
    ]
    if cell_value.upper() in single_word_rejects:
        return False
    
    if re.match(r'^[\d]+[A-Z](/[A-Z])?$', cell_value):
        return False
    
    words = cell_value.split()
    
    if 'HRT' in cell_value.upper():
        return True
    
    if len(words) < 2:
        return False
    
    if all(len(word) <= 2 for word in words):
        return False
    
    return True

def clean_teacher_name(raw_name: str) -> str:
    """Cleans teacher names by removing HRT prefix and extra formatting."""
    name = str(raw_name).strip()
    name = re.sub(r'\bHRT\b\s*-?\s*', '', name, flags=re.IGNORECASE).strip()
    name = re.sub(r'\s*\([^)]*\)', '', name).strip()
    name = re.sub(r'\s*-\s*[\d,A-Z/\s]+$', '', name).strip()
    
    if ',' in name:
        name = name.split(',')[0].strip()
    
    name = re.sub(r'/[A-Z]', '', name).strip()
    return name

def generate_valid_email(teacher_name: str) -> str:
    """Generates a valid email address from a teacher name."""
    email_local = teacher_name.lower()
    email_local = email_local.replace(' ', '')
    email_local = re.sub(r'[^a-z0-9._-]', '', email_local)
    email_local = email_local.strip('.-')
    
    if not email_local:
        email_local = 'teacher'
    
    return f"{email_local}@school.edu"

def parse_time_slot(time_str: str) -> tuple[str, str] | None:
    """Extracts start and end times from a string like '08:30 - 09:10'."""
    time_str = str(time_str).strip()
    
    if 'BREAK' in time_str.upper() or 'LUNCH' in time_str.upper():
        return None
    
    time_parts = re.split(r'\s*[-–]\s*', time_str)
    if len(time_parts) == 2:
        start = time_parts[0].strip().replace('.', ':')
        end = time_parts[1].strip().replace('.', ':')
        
        if ':' in start and ':' in end:
            return start, end
    
    return None

def find_weekday_row(df_raw: pd.DataFrame, start_row: int, search_range: int = 10) -> tuple[int, int] | None:
    """Finds the row containing weekdays (Monday-Friday) near a teacher name."""
    for row_idx in range(start_row, min(start_row + search_range, len(df_raw))):
        for col_idx in range(len(df_raw.columns)):
            cell_value = str(df_raw.iloc[row_idx, col_idx]).strip()
            if cell_value == 'Monday':
                if col_idx + 4 < len(df_raw.columns):
                    next_cells = [str(df_raw.iloc[row_idx, col_idx + i]).strip() 
                                for i in range(1, 5)]
                    if 'Tuesday' in next_cells:
                        return row_idx, col_idx
    return None

def parse_teacher_timetables(db: Session, contents: bytes) -> Dict[str, Any]:
    """Reads the timetable CSV and parses teacher schedules."""
    
    try:
        df_raw = pd.read_excel(BytesIO(contents), header=None)
    except Exception:
        try:
            content_str = contents.decode('utf-8-sig')
            df_raw = pd.read_csv(StringIO(content_str), header=None)
        except Exception as e:
            raise ValueError(f"Could not read file. Error: {e}")
    
    subject_mapping = parse_subject_mapping(df_raw)
    
    teachers_processed = 0
    total_entries = 0
    teacher_blocks = []
    
    for row_idx in range(len(df_raw)):
        for col_idx in range(len(df_raw.columns)):
            cell_value = str(df_raw.iloc[row_idx, col_idx]).strip()
            
            if is_teacher_name_cell(cell_value):
                weekday_info = find_weekday_row(df_raw, row_idx + 1, search_range=3)
                
                if weekday_info:
                    weekday_row, monday_col = weekday_info
                    teacher_name = clean_teacher_name(cell_value)
                    time_col = monday_col - 1
                    
                    if teacher_name and time_col >= 0:
                        teacher_blocks.append({
                            'name': teacher_name,
                            'header_row': row_idx,
                            'weekday_row': weekday_row,
                            'time_col': time_col,
                            'monday_col': monday_col
                        })
    
    if not teacher_blocks:
        raise ValueError("No teacher blocks found. Please check the file format.")
    
    db.query(models.TimetableEntry).delete(synchronize_session=False)
    
    weekdays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    
    for block in teacher_blocks:
        teacher_name = block['name']
        time_col = block['time_col']
        monday_col = block['monday_col']
        weekday_row = block['weekday_row']
        
        teacher_email = generate_valid_email(teacher_name)
        teacher = db.query(models.Teacher).filter(models.Teacher.email == teacher_email).first()
        if not teacher:
            teacher = models.Teacher(name=teacher_name, email=teacher_email, is_admin=False)
            db.add(teacher)
            db.flush()
        teacher_id = teacher.id
        
        end_row = len(df_raw)
        for next_block in teacher_blocks:
            if next_block['header_row'] > block['header_row']:
                end_row = next_block['header_row']
                break
        
        new_entries = []
        
        for row_idx in range(weekday_row + 1, end_row):
            time_cell = df_raw.iloc[row_idx, time_col]
            
            if pd.isna(time_cell) or str(time_cell).strip() == '':
                continue
            
            time_str = str(time_cell).strip()
            
            if 'BREAK' in time_str.upper():
                continue
            
            time_parts = parse_time_slot(time_str)
            if not time_parts:
                continue
            
            start_time_str, end_time_str = time_parts
            
            for day_idx, day_name in enumerate(weekdays):
                col_idx = monday_col + day_idx
                
                if col_idx >= len(df_raw.columns):
                    continue
                
                class_cell = df_raw.iloc[row_idx, col_idx]
                
                if pd.isna(class_cell) or str(class_cell).strip() == '':
                    continue
                
                class_name_raw = str(class_cell).strip()
                
                if 'BREAK' in class_name_raw.upper():
                    continue
                
                subject = get_subject_from_mapping_or_class(teacher_name, class_name_raw, subject_mapping)
                
                entry = models.TimetableEntry(
                    teacher_id=teacher_id,
                    day_of_week=day_name,
                    start_time=start_time_str,
                    end_time=end_time_str,
                    class_name=class_name_raw,
                    subject=subject,
                    is_free=False
                )
                new_entries.append(entry)
                total_entries += 1
        
        if new_entries:
            db.add_all(new_entries)
            teachers_processed += 1
    
    db.commit()
    return {
        "teachers_processed": teachers_processed, 
        "total_entries": total_entries,
        "subject_mappings": len(subject_mapping)
    }

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
                .info { background: #e0f2fe; padding: 15px; border-radius: 6px; margin-bottom: 20px; }
                .info h3 { margin-top: 0; color: #0369a1; }
                .info ul { margin: 10px 0; }
                form { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); display: flex; gap: 15px; align-items: center; }
                input[type="file"] { padding: 10px; border: 1px solid #ddd; border-radius: 4px; }
                button { background-color: #4f46e5; color: white; padding: 10px 15px; border: none; border-radius: 4px; cursor: pointer; transition: background-color 0.2s; }
                button:hover { background-color: #4338ca; }
            </style>
        </head>
        <body>
            <h2>📘 Upload Master Timetable (Excel/CSV)</h2>
            
            <div class="info">
                <h3>File Format Requirements:</h3>
                <ul>
                    <li><strong>Teacher Names:</strong> Should NOT contain "HRT-3A" or "NON-HRT" patterns</li>
                    <li><strong>Structure:</strong> Time slots in column 1, then Monday through Friday</li>
                    <li><strong>Optional:</strong> Include subject mapping section with subject names and teacher lists</li>
                    <li><strong>Breaks:</strong> SNACKS BREAK and LUNCH BREAK will be automatically skipped</li>
                </ul>
            </div>
            
            <form action="/timetable/upload-master" enctype="multipart/form-data" method="post">
                <input name="file" type="file" accept=".csv,.xlsx,.xls" required>
                <button type="submit">Upload & Process</button>
            </form>
        </body>
    </html>
    """

@router.post("/upload-master", status_code=status.HTTP_201_CREATED)
async def upload_master_timetable(
    file: UploadFile,
    db: Session = Depends(get_db)
):
    """
    Uploads the master timetable file, parses the layout,
    and replaces all existing timetable data.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided.")
        
    if not file.filename.endswith(('.csv', '.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a CSV, XLS, or XLSX file.")
    
    try:
        contents = await file.read()
        result = parse_teacher_timetables(db, contents)
        
        message = f"Master timetable uploaded successfully for {result['teachers_processed']} teachers."
        if result['subject_mappings'] > 0:
            message += f" Found {result['subject_mappings']} subject mappings."
        
        return {
            "message": message,
            "total_entries": result['total_entries'],
            "teachers_processed": result['teachers_processed'],
            "subject_mappings": result['subject_mappings']
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to process timetable. Error: {type(e).__name__}: {str(e)}")

@router.get("/test")
async def test_endpoint():
    """Simple test endpoint to verify router is working."""
    return {"status": "Timetable router is working!", "endpoints_available": True}