from app import create_app, db
from models import Order, OrderItem, Item, Store, Subsite
import os

# Set Env for Tunnel (Production)
os.environ['DB_HOST'] = '127.0.0.1:3307'
os.environ['DB_NAME'] = 'lanches_da_op'
os.environ['DB_USER'] = 'root'
os.environ['DB_PASSWORD'] = 'CodeEz4ever'

app = create_app()

def test_query():
    with app.app_context():
        print(f"DB URI: {app.config['SQLALCHEMY_DATABASE_URI']}")
        print("--- Testing Dispatcher Query Logic ---")
        
        # 1. Get Store 1
        store = Store.query.get(1)
        print(f"Store: {store.name} (ID: {store.id})")
        
        # 2. Get Subsite 11
        subsite = Subsite.query.get(11)
        print(f"Subsite: {subsite.name} (ID: {subsite.id})")
        
        # 3. Build Query step-by-step
        print("\n--- Filter 1: Subsite 11 ---")
        q1 = Order.query.filter(Order.subsite_id == subsite.id)
        print(f"Count: {q1.count()}")
        for o in q1.all():
            print(f" - Found Order ID: {o.id}, Subsite: {o.subsite_id}, Disp: {o.whatsapp_dispatched}")
        
        # Test Variations
        print("\n--- Testing Boolean Filters ---")
        
        print("1. == False")
        c1 = q1.filter(Order.whatsapp_dispatched == False).count()
        print(f"Count: {c1}")

        print("2. == 0")
        c2 = q1.filter(Order.whatsapp_dispatched == 0).count()
        print(f"Count: {c2}")

        print("3. is_(False)")
        c3 = q1.filter(Order.whatsapp_dispatched.is_(False)).count()
        print(f"Count: {c3}")
        
        print("5. != 1")
        c5 = q1.filter(Order.whatsapp_dispatched != 1).count()
        print(f"Count: {c5}")
        
        print("6. isnot(True)")
        c6 = q1.filter(Order.whatsapp_dispatched.isnot(True)).count()
        print(f"Count: {c6}")

        print("\n--- Filter 2 Redux ---")
        q2 = q1.filter(Order.whatsapp_dispatched != 1)
        print(f"Count: {q2.count()}")
        # Check if Order 8 is here
        o8 = q2.filter(Order.id == 8).first()
        print(f"Order 8 present? {o8 is not None}")
        
        print("\n--- Filter 3: + Store 1 (via Join) ---")
        q3 = q2.join(OrderItem).join(Item).filter(Item.store_id == store.id)
        print(f"Count: {q3.count()}")
        print("\n--- Filter 3 SQL ---")
        # print(str(q3.statement.compile(compile_kwargs={"literal_binds": True}))) 
        # (literal_binds might fail on some types, but let's try basic str)
        print(str(q3))
        
        print("\n--- Filter 3 Execution ---")
        results = q3.all()
        print(f"Found {len(results)} orders.")
        for o in results:
            print(f" - Order {o.id}: Dispatched={o.whatsapp_dispatched}")

if __name__ == "__main__":
    test_query()
