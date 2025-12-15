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
            
        print("\n--- Verifying Soft Delete Simulation ---")
        # Simulate logic: soft delete sets active=False
        test_sec = Sector(name="Mesa Teste Delete", subsite_id=subsite_id, active=True, type='location')
        db.session.add(test_sec)
        db.session.commit()
        print(f"Created: {test_sec.name} (Active: {test_sec.active})")
        
        # Soft delete action
        test_sec.active = False
        db.session.commit()
        print(f"Deleted (Soft): {test_sec.name} (Active: {test_sec.active})")
        
        # Verify visibility
        visible = Sector.query.filter(
            (Sector.subsite_id == subsite_id) & 
            ((Sector.type == 'location') | (Sector.type == None)) &
            (Sector.active == True) # This is crucial
        ).all()
        
        if any(s.name == "Mesa Teste Delete" for s in visible):
            print("FAILURE: Soft deleted item still visible!")
        else:
            print("SUCCESS: Soft deleted item correctly hidden.")
            
        # Cleanup
        db.session.delete(test_sec)
        db.session.commit()

if __name__ == "__main__":
    check()
