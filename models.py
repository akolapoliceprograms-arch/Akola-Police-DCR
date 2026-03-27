from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Date, JSON, Boolean, Text
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime, date

Base = declarative_base()

class Unit(Base):
    """
    Represents a Police Station or Administrative Unit.
    """
    __tablename__ = "units"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    division = Column(String(100), nullable=False)
    password_hash = Column(String(255), default="Akola123")  # Simplified for now
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    reports = relationship("DailyReport", back_populates="unit")

class DailyReport(Base):
    """
    Represents the daily operational submission from a Unit.
    """
    __tablename__ = "daily_reports"
    
    id = Column(Integer, primary_key=True, index=True)
    unit_id = Column(Integer, ForeignKey("units.id"), nullable=False)
    report_date = Column(Date, default=date.today, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Metadata for submission tracking
    is_submitted = Column(Boolean, default=False)
    submitted_by = Column(String(100))
    
    # Operational Data (Structured)
    # Operational Data (Structured)
    officers_on_duty = Column(Integer, default=0)
    personnel_on_duty = Column(Integer, default=0)
    
    officers_breakdown = Column(JSON)
    personnel_breakdown = Column(JSON)
    
    # JSON Blobs for flexible section data
    naka_bandi_stats = Column(JSON)      # {vehicles_checked: int, action_details: str}
    patrolling_stats = Column(JSON)      # {route: str, findings: str}
    crime_stats = Column(JSON)           # {cctns_reg: int, gd_entries: int, etc}
    mobile_tracking_stats = Column(JSON) # {imei_tracked: int, results: str}
    
    # General Remarks
    remarks = Column(Text)

    unit = relationship("Unit", back_populates="reports")
