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
        print("--- Testing Dispatcher Query Logic (Store Only) ---")
        
        # Target Store ID 1
        store_id = 1
        print(f"Target Store ID: {store_id}")

        # Query: Order -> OrderItem -> Item (Store=1) + Dispatched=False
        q = Order.query.join(OrderItem).join(Item).filter(Item.store_id == store_id)
        q = q.filter(Order.whatsapp_dispatched == False)
        
        print(f"SQL: {q.statement}")
        print(f"Count: {q.count()}")
        
        orders = q.all()
        for o in orders:
             print(f" - Found Order ID: {o.id}, Subsite: {o.subsite_id}, Disp: {o.whatsapp_dispatched}")
             
        # Check Order 8 specific linkage
        print("\n--- Order 8 Analysis ---")
        o8 = Order.query.get(8)
        if o8:
            print(f"Order 8 loaded. Subsite: {o8.subsite_id}, Disp: {o8.whatsapp_dispatched}")
            for oi in o8.order_items:
                i = Item.query.get(oi.item_id)
                print(f" - Item {i.id}: {i.name}, Store: {i.store_id}")
        else:
            print("Order 8 NOT found via SQLAlchemy.")

if __name__ == "__main__":
    test_query()
