from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import models as m
from datetime import datetime

# --- Configuration ---
DATABASE_URL = "sqlite:///./dpr_portal.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)

def seed_database():
    """
    Seeds the database with Akola Police Stations across 4 Sub-Divisions.
    Using user-provided official list with Marathi names.
    """
    db = SessionLocal()
    
    # Initialize Schema (DANGER: Wipes existing data)
    print("\n[!] Wiping existing data for fresh installation...")
    m.Base.metadata.drop_all(bind=engine)
    m.Base.metadata.create_all(bind=engine)
    
    divisions = {
        "Akola Shahar (City) Division": [
            "City Kotwali (सिटी कोतवाली)", "Ramdaspeth (रामदासपेठ)", "Civil Lines (सिव्हिल लाईन्स)", 
            "Old City (जुना शहर)", "Akot File (अकोट फाईल)", "Khadan (खदान)", 
            "Dabki Road (डाबकी रोड)", "M.I.D.C. (एम.आय.डी.सी.)"
        ],
        "Akot Division": [
            "Akot City (अकोट शहर)", "Akot Rural (अकोट ग्रामीण)", "Dahihanda (दहिहांडा)", 
            "Telhara (तेल्हारा)", "Hiwarkhed (हिवरखेड)"
        ],
        "Murtizapur Division": [
            "Murtizapur City (मुर्तीजापूर शहर)", "Murtizapur Rural (मुर्तीजापूर ग्रामीण)", 
            "Borgaon Manju (बोरगाव मंजू)", "Barshitakli (बार्शीटाकळी)", "Pinjar (पिंजर)", "Mana (माना)"
        ],
        "Balapur Division": [
            "Balapur (बाळापूर)", "Patur (पातूर)", "Channi (चन्नी)", "Ural (उरळ)"
        ]
    }
    
    print("[+] Initializing Akola Police Administrative Schema...")
    
    total_stations = 0
    for div_name, stations in divisions.items():
        for station in stations:
            unit = m.Unit(
                name=station,
                division=div_name,
                password_hash="Akola123",
                is_active=True
            )
            db.add(unit)
            total_stations += 1
    
    db.commit()
    print(f"[+] Successfully Seeded {total_stations} Operational Units.")
    db.close()

if __name__ == "__main__":
    seed_database()
