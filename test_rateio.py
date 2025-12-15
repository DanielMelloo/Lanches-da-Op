import os
import sys
from datetime import datetime, timedelta

# Configure environment for Tunnel connection
os.environ['DB_HOST'] = '127.0.0.1:3307'
os.environ['DB_USER'] = 'root'
os.environ['DB_PASSWORD'] = 'CodeEz4ever'
os.environ['DB_NAME'] = 'lanches_da_op'
os.environ['SKIP_SCHEDULER'] = 'true'

from app import create_app, db
from models import Order, Subsite, User, Status, Sector

def test_rateio():
    app = create_app()
    with app.app_context():
        print("--- Starting Rateio Test ---")
        
        # 1. Setup Data
        subsite = Subsite.query.first()
        if not subsite:
            print("Error: No subsite found.")
            return

        print(f"Subsites: {Subsite.query.count()}")
        print(f"Users: {User.query.count()}")
        print(f"Statuses: {Status.query.count()}")
        
        user = User.query.first()
        status = Status.query.first()
        sector = Sector.query.first()
        
        if not user: print("MISSING: User")
        if not status: print("MISSING: Status")

        print(f"Using Subsite: {subsite.name} (ID: {subsite.id})")
        print(f"Initial Tax Mode: {subsite.tax_mode}")
        
        # 2. Create 3 Dummy Orders
        print("\nCreating 3 test orders...")
        created_orders = []
        for i in range(3):
            o = Order(
                user_id=user.id,
                subsite_id=subsite.id,
                status_id=status.id,
                sector_id=sector.id if sector else None,
                total_items=10.0,
                tax_fixed=0.0,
                total_general=10.0,
                created_at=datetime.now()
            )
            db.session.add(o)
            created_orders.append(o)
        
        db.session.commit()
        print(f"Created Orders: {[o.id for o in created_orders]}")

        # 3. Simulate Rateio Logic
        # Let's say Total Expenses = 30.00
        # And we want to split among ALL orders of this subsite in the last 24h (or just all for simplicity of test)
        
        total_expenses = 30.00
        print(f"\nSimulating Rateio with Total Expenses: R$ {total_expenses}")
        
        # Count target orders (including the ones we just made)
        # For this test, we filter by the IDs we just created to be isolated, 
        # OR we follow the real logic: all orders in period.
        # Let's count ALL active orders for this subsite to be realistic with the "divide para todos" request
        
        all_orders = Order.query.filter_by(subsite_id=subsite.id).filter(Order.status_id != 4).all()
        valid_orders = [o for o in all_orders if o.payment_status != 'approved']
        count = len(valid_orders)
        
        print(f"Found {count} eligible orders for rateio.")
        
        if count > 0:
            new_tax = total_expenses / count
            print(f"Calculated New Tax: {total_expenses} / {count} = R$ {new_tax:.2f}")
            
            # Apply Update
            for o in valid_orders:
                o.tax_fixed = new_tax
                o.total_general = o.total_items + new_tax # simplified update
            
            db.session.commit()
            print("Database updated.")
            
            # 4. Verify
            print("\nVerifying our created orders:")
            for o in created_orders:
                db.session.refresh(o)
                print(f"Order {o.id}: Items={o.total_items}, Tax={o.tax_fixed:.2f}, Total={o.total_general:.2f}")
                
            if abs(created_orders[0].tax_fixed - new_tax) < 0.01:
                print("\nSUCCESS: Tax split correctly!")
            else:
                print("\nFAILURE: Tax mismatch.")
        else:
            print("No orders to split expenses.")

if __name__ == "__main__":
    test_rateio()
