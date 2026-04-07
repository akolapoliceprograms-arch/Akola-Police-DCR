from fastapi import FastAPI, Depends, HTTPException, status, Body
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import models as m
from datetime import datetime, date, timedelta
import uvicorn
import os
import pandas as pd
import io

# --- Database Setup ---
import os
# Use Supabase Lifetime Free Database directly
# (Overrides Render's expiring database variable completely)
# Password is URL encoded because it contains '@' and '#'
DATABASE_URL = "postgresql://postgres.djnebvjenrjhaksrywbq:Akola%40123%23%23123@aws-1-ap-northeast-1.pooler.supabase.com:6543/postgres"

engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(bind=engine, autoflush=False)

# Initialize Tables (Automated for this fresh start)
m.Base.metadata.create_all(bind=engine)

# Auto-seed if empty (fixes blank stations on Render deployments)
db = SessionLocal()
try:
    if db.query(m.Unit).count() == 0:
        import seed
        # seed.py drops and recreates tables, then seeds police stations.
        # This is safe to run since we just ensured the table is completely empty.
        seed.seed_database()
finally:
    db.close()

from fastapi.staticfiles import StaticFiles

# --- FastAPI App ---
app = FastAPI(
    title="Akola Police DCR Portal",
    description="Internal portal for Daily Crime Report management.",
    version="1.0.0"
)

# Ensure static folder exists locally for custom images
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Optional: Enable CORS if testing from different origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

# --- Routes ---

@app.get("/", tags=["Dashboard"])
async def read_index():
    """Serves the main command center interface."""
    return FileResponse('index.html')

@app.get("/api/seed", tags=["Setup"])
def manual_seed():
    """Manually triggers the official police station seeding algorithm."""
    try:
        import seed
        seed.seed_database()
        return {"status": "success", "message": "24 Police Stations explicitly seeded to active database."}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/units", tags=["Metadata"])
def list_units(db: Session = Depends(get_db)):
    """Retrieve all operational police units/stations."""
    units = db.query(m.Unit).filter(m.Unit.is_active == True).order_by(m.Unit.name).all()
    return [{"id": u.id, "name": u.name, "division": u.division} for u in units]

@app.post("/api/report/submit", tags=["Operations"])
def submit_report(
    unit_id: int, 
    report_data: dict = Body(...), 
    db: Session = Depends(get_db)
):
    """
    Submits or updates a daily case report (DCR).
    The report_data JSON will be mapped to the model fields.
    """
    # Check if a report for this unit and today already exists
    today = date.today()
    existing_report = db.query(m.DailyReport).filter(
        m.DailyReport.unit_id == unit_id,
        m.DailyReport.report_date == today
    ).first()

    # Filter out any extra keys from report_data that don't belong to the DailyReport model
    valid_keys = {
        "officers_on_duty", "personnel_on_duty", "officers_breakdown", "personnel_breakdown", "naka_bandi_stats", 
        "patrolling_stats", "crime_stats", "mobile_tracking_stats", "remarks", "is_submitted", "submitted_by"
    }
    filtered_data = {k: v for k, v in report_data.items() if k in valid_keys}

    if existing_report:
        # Update existing
        for key, value in filtered_data.items():
            setattr(existing_report, key, value)
        existing_report.timestamp = datetime.utcnow()
    else:
        # Create new
        new_report = m.DailyReport(
            unit_id=unit_id,
            report_date=today,
            **filtered_data
        )
        db.add(new_report)
    
    # Auto-cleanup logic has been removed as per user request to not delete old data after 30 days.
    
    db.commit()
    return {"status": "success", "message": "DCR Transmitted Successfully"}

@app.get("/api/admin/tracker", tags=["Monitoring"])
def get_tracker(date_query: str | None = None, db: Session = Depends(get_db)):
    """
    Provides a real-time snapshot of report submissions across all units.
    Used by the Command Center (Admin View).
    """
    try:
        target_date = datetime.strptime(date_query, "%Y-%m-%d").date() if date_query else date.today()
    except (ValueError, TypeError):
        target_date = date.today()
    
    units = db.query(m.Unit).all()
    tracker_data = []
    
    for unit in units:
        report = db.query(m.DailyReport).filter(
            m.DailyReport.unit_id == unit.id,
            m.DailyReport.report_date == target_date
        ).first()
        
        last_sync = None
        if report and report.timestamp:
            try:
                last_sync = report.timestamp.strftime("%H:%M")
            except:
                last_sync = "??:??"

        tracker_data.append({
            "id": unit.id,
            "station": unit.name,
            "division": unit.division,
            "is_submitted": True if report else False,
            "last_sync": last_sync,
            "stats": {
                "staff": {
                    "officers": report.officers_on_duty if report else 0,
                    "personnel": report.personnel_on_duty if report else 0
                },
                "naka_bandi": report.naka_bandi_stats if report else {},
                "crime": report.crime_stats if report else {},
                "mobile": report.mobile_tracking_stats if report else {}
            }
        })
    
    return tracker_data

@app.get("/api/report/details/{unit_id}", tags=["Monitoring"])
def get_report_details(unit_id: int, date_query: str | None = None, db: Session = Depends(get_db)):
    """Fetches full report data for a specific station/unit on a given date."""
    try:
        target_date = datetime.strptime(date_query, "%Y-%m-%d").date() if date_query else date.today()
    except (ValueError, TypeError):
        target_date = date.today()
        
    report = db.query(m.DailyReport).filter(
        m.DailyReport.unit_id == unit_id,
        m.DailyReport.report_date == target_date
    ).first()
    
    if not report:
        raise HTTPException(status_code=404, detail="No report found for this unit on the requested date.")
        
    return {
        "unit_name": report.unit.name,
        "division": report.unit.division,
        "report_date": report.report_date,
        "timestamp": report.timestamp,
        "officers_on_duty": report.officers_on_duty,
        "personnel_on_duty": report.personnel_on_duty,
        "naka_bandi_stats": report.naka_bandi_stats,
        "patrolling_stats": report.patrolling_stats,
        "crime_stats": report.crime_stats,
        "mobile_tracking_stats": report.mobile_tracking_stats,
        "remarks": report.remarks
    }

@app.get("/api/export/all", tags=["Export"])
def export_all_reports(date_query: str | None = None, db: Session = Depends(get_db)):
    """Generates a consolidated Excel report for all stations on a given date."""
    try:
        target_date = datetime.strptime(date_query, "%Y-%m-%d").date() if date_query else date.today()
    except (ValueError, TypeError):
        target_date = date.today()
    reports = db.query(m.DailyReport).filter(m.DailyReport.report_date == target_date).all()
    
    data = []
    for r in reports:
        data.append({
            "Station": r.unit.name,
            "Division": r.unit.division,
            "Report Date": r.report_date,
            "Sync Time": r.timestamp.strftime("%H:%M:%S"),
            "Officers": r.officers_on_duty,
            "Personnel": r.personnel_on_duty,
            "Vehicles Checked": r.naka_bandi_stats.get('vehicles_checked', 0) if r.naka_bandi_stats else 0,
            "Naka Bandi Details": r.naka_bandi_stats.get('action_details', '') if r.naka_bandi_stats else '',
            "Patrol Route": r.patrolling_stats.get('route', '') if r.patrolling_stats else '',
            "Patrol Findings": r.patrolling_stats.get('findings', '') if r.patrolling_stats else '',
            "FIRs": r.crime_stats.get('new_firs', 0) if r.crime_stats else 0,
            "IMEI Tracked": r.mobile_tracking_stats.get('imei_tracked', 0) if r.mobile_tracking_stats else 0
        })
    
    df = pd.DataFrame(data)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Consolidated DCR')
    
    output.seek(0)
    from urllib.parse import quote
    encoded_filename = quote(f"AKOLA_DCR_CONSOLIDATED_{target_date}.xlsx")
    headers = {'Content-Disposition': f"attachment; filename*=UTF-8''{encoded_filename}"}
    return StreamingResponse(output, headers=headers, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

@app.get("/api/export/unit/{unit_id}", tags=["Export"])
def export_unit_report(unit_id: int, db: Session = Depends(get_db)):
    """Generates a detailed Excel report for a specific unit (all time history)."""
    unit = db.query(m.Unit).filter(m.Unit.id == unit_id).first()
    if not unit: raise HTTPException(404, "Unit not found")
    
    reports = db.query(m.DailyReport).filter(m.DailyReport.unit_id == unit_id).order_by(m.DailyReport.report_date.desc()).all()
    
    data = []
    for r in reports:
        data.append({
            "Date": r.report_date,
            "Officers": r.officers_on_duty,
            "Personnel": r.personnel_on_duty,
            "Naka Bandi Vehicles": r.naka_bandi_stats.get('vehicles_checked', 0) if r.naka_bandi_stats else 0,
            "Naka Bandi Action": r.naka_bandi_stats.get('action_details', '') if r.naka_bandi_stats else '',
            "Patrolling Route": r.patrolling_stats.get('route', '') if r.patrolling_stats else '',
            "FIRs": r.crime_stats.get('new_firs', 0) if r.crime_stats else 0,
            "IMEIs Tracked": r.mobile_tracking_stats.get('imei_tracked', 0) if r.mobile_tracking_stats else 0
        })
    
    # Sanitize sheet name for Excel (max 31 chars, no special symbols)
    sheet_name = unit.name[:25] + " History"
    sheet_name = "".join(c for c in sheet_name if c not in r'[]*?/\:')[:31]
    
    df = pd.DataFrame(data)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
    
    output.seek(0)
    # Safe filename for headers (RFC 5987)
    from urllib.parse import quote
    encoded_filename = quote(f"REPORT_{unit.name}.xlsx")
    headers = {'Content-Disposition': f"attachment; filename*=UTF-8''{encoded_filename}"}
    return StreamingResponse(output, headers=headers, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

if __name__ == "__main__":
    print("\n[+] Akola Police DCR Portal - Initializing Engine...")
    print("[+] Console: http://localhost:8001/docs")
    print("[+] Portal: http://localhost:8001")
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
