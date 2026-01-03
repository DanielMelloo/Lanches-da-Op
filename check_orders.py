import os
# Override DB config to point to SSH Tunnel (Production)
os.environ['DB_HOST'] = '127.0.0.1:3307'
os.environ['DB_USER'] = 'root'
os.environ['DB_PASSWORD'] = 'CodeEz4ever'
os.environ['DB_NAME'] = 'lanches_da_op'

from app import create_app, db
from models import Order, OrderItem, Item, Sector

app = create_app()

with app.app_context():
    # Get last 3 orders
    orders = Order.query.order_by(Order.id.desc()).limit(3).all()
    if orders:
        for order in orders:
            print(f"--- Order ID: {order.id} ---")
            user_name = order.user.name if order.user else 'Unknown'
            print(f"Customer: {user_name}")
            print(f"Items Count: {len(order.order_items)}")
            
            for oi in order.order_items:
                item_name = oi.item.name if oi.item else "Unknown Item"
                store_id = oi.item.store_id if oi.item else "None"
                
                store_name = "Unknown"
                if oi.item and oi.item.store:
                    store_name = oi.item.store.name
                
                print(f" - {oi.quantity}x {item_name}")
                print(f"   -> Pertence à Loja: {store_name} (ID: {store_id})")
            print("")
            
    else:
        print("No orders found.")
