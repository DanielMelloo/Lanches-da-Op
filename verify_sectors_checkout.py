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

if __name__ == "__main__":
    check()
