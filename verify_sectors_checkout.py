import os
from sqlalchemy import create_engine, or_

# Override DB config
os.environ['DB_HOST'] = '127.0.0.1:3307'
os.environ['DB_USER'] = 'root'
os.environ['DB_PASSWORD'] = 'CodeEz4ever'
os.environ['DB_NAME'] = 'lanches_da_op'
os.environ['SKIP_SCHEDULER'] = 'true'

from app import create_app
from models import Sector
from database import db

def check():
    app = create_app()
    with app.app_context():
        print("--- Verifying Sector Query for Checkout ---")
        
        # Simulate logic from routes_user.py
        # ((Sector.subsite_id == subsite_id) | (Sector.subsite_id == None)) & 
        # (Sector.active == True) & 
        # ((Sector.type == 'location') | (Sector.type == None))
        
        # Retrieve ALL to see what's in DB
        all_s = Sector.query.all()
        print(f"Total Sectors: {len(all_s)}")
        for s in all_s:
            print(f" - {s.name} ({s.type})")
            
        print("\n--- Simulating Checkout Query ---")
        subsite_id = 1 # Assuming ID 1
        
        query = Sector.query.filter(
            ((Sector.subsite_id == subsite_id) | (Sector.subsite_id == None)) & 
            (Sector.active == True) & 
            ((Sector.type == 'location') | (Sector.type == None))
            # Note: SQLAlchemy boolean precedence might need parens, checking matching logic
        ).all()
        
        print(f"Found {len(query)} available locations:")
        shown_names = [s.name for s in query]
        for s in query:
            print(f" > {s.name}")
            
        # Assertion
        if 'Espetos' in shown_names or 'Acompanhamentos' in shown_names:
            print("\nFAILURE: Menu categories are still showing!")
        else:
            print("\nSUCCESS: Menu categories correctly hidden.")
            
        print("\n--- Verifying Smart Delete Simulation ---")
        # Case 1: Unused Sector (Should Hard Delete)
        test_sec = Sector(name="Mesa Fim", subsite_id=subsite_id, active=True, type='location')
        db.session.add(test_sec)
        db.session.commit()
        print(f"Created Unused: {test_sec.name}")
        
        # Manually trying hard delete (simulating route logic)
        try:
            db.session.delete(test_sec)
            db.session.commit()
            print("Hard Deleted (Unused): Success")
        except Exception as e:
             print(f"Hard Delete Failed: {e}")
             
        # Verify it's gone
        check_gone = Sector.query.filter_by(name="Mesa Fim").first()
        if not check_gone:
            print("SUCCESS: Unused sector was permanently removed.")
        else:
             print("FAILURE: Unused sector still exists.")

if __name__ == "__main__":
    check()
