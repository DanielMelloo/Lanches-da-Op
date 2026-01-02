import os
import time
import json
import urllib.parse
from datetime import datetime
from playwright.sync_api import sync_playwright
from app import create_app
from database import db
from models import Subsite, Order, Store, OrderItem, Item

def format_order_summary(store, orders_data):
    """Formats a message with all orders for a specific store."""
    if not orders_data:
        return None
        
    msg = f"*RESUMO DE PEDIDDOS - {store.name}*\n"
    msg += f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n"
    msg += "----------------------------\n\n"
    
    for order_id, items in orders_data.items():
        msg += f"*Pedido #{order_id}*\n"
        for item in items:
            msg += f"• {item['quantity']}x {item['name']}\n"
            if item.get('subitems'):
                msg += f"  _Opcionais: {item['subitems']}_\n"
        msg += "\n"
        
    msg += "----------------------------\n"
    msg += "Favor confirmar o recebimento."
    return msg

def run_dispatcher():
    app = create_app()
    with app.app_context():
        # 1. Find targets for dispatch
        # - Stores from closed subsites
        # - Stores with manual dispatch pending
        active_subsites = Subsite.query.filter_by(active=True).all()
        closed_subsites = [s for s in active_subsites if not s.is_open()]
        manual_stores = Store.query.filter_by(pending_manual_dispatch=True).all()
        
        if not closed_subsites and not manual_stores:
            print(f"[{datetime.now()}] Nothing to dispatch. Skipping.")
            return

        dispatches = {} # {whatsapp_number: {store_obj: {order_id: [items]}}}
        orders_to_mark = set()

        # Helper to process a store's pending orders
        def process_store_orders(store, specific_subsite_id=None):
            if not store.whatsapp_number:
                return
            
            num = store.whatsapp_number.strip().replace('+', '').replace(' ', '').replace('-', '')
            if not num: return
            if len(num) in [10, 11]: num = '55' + num
            
            # Query undispatched orders containing items for this store
            query = Order.query.filter_by(whatsapp_dispatched=False).join(OrderItem).join(Item).filter(Item.store_id == store.id)
            if specific_subsite_id:
                query = query.filter(Order.subsite_id == specific_subsite_id)
            
            pending_orders = query.all()
            if not pending_orders:
                return

            if num not in dispatches: dispatches[num] = {}
            if store not in dispatches[num]: dispatches[num][store] = {}

            for order in pending_orders:
                orders_to_mark.add(order)
                if order.id not in dispatches[num][store]:
                    dispatches[num][store][order.id] = []
                
                # Only items for THIS store in this order
                for oi in order.order_items:
                    if not oi.item or oi.item.store_id != store.id:
                        continue
                        
                    # Extract subitems
                    subtext = ""
                    if oi.subitems_json:
                        parts = []
                        for group in oi.subitems_json:
                            opts = group.get('options', [])
                            if opts:
                                opt_names = []
                                for o in opts:
                                    if isinstance(o, dict): opt_names.append(f"{o.get('option')} x{o.get('qty', 1)}")
                                    else: opt_names.append(str(o))
                                parts.append(f"{group.get('title', group.get('group', ''))}: {', '.join(opt_names)}")
                        subtext = " | ".join(parts)

                    dispatches[num][store][order.id].append({
                        'name': oi.item.name,
                        'quantity': oi.quantity,
                        'subitems': subtext
                    })

        # Process closed subsites
        for subsite in closed_subsites:
            subsite_stores = Store.query.filter_by(subsite_id=subsite.id).all()
            for s in subsite_stores:
                process_store_orders(s, subsite.id)
        
        # Process manual triggers
        for s in manual_stores:
            process_store_orders(s)
            s.pending_manual_dispatch = False

        if not dispatches:
            print(f"[{datetime.now()}] No orders grouped for dispatch.")
            db.session.commit() # Flush manual flags
            return

        # 3. Send via WhatsApp Web (Playwright)
        user_data_dir = os.path.join(os.getcwd(), "whatsapp_session")
        
        with sync_playwright() as p:
            browser = p.chromium.launch_persistent_context(
                user_data_dir,
                headless=False,
                args=['--no-sandbox']
            )
            page = browser.new_page()
            print("Opening WhatsApp Web...")
            page.goto("https://web.whatsapp.com/")
            
            try:
                page.wait_for_selector('div[contenteditable="true"]', timeout=30000)
            except:
                print("Action Required: Please log in to WhatsApp Web.")
                page.wait_for_selector('div[contenteditable="true"]', timeout=300000)

            for num, stores_dict in dispatches.items():
                for store, orders_data in stores_dict.items():
                    message = format_order_summary(store, orders_data)
                    if not message: continue
                        
                    print(f"Sending to {store.name} ({num})...")
                    encoded_msg = urllib.parse.quote(message)
                    page.goto(f"https://web.whatsapp.com/send?phone={num}&text={encoded_msg}")
                    
                    try:
                        # Wait for send button and click
                        send_btn = page.wait_for_selector('span[data-icon="send"]', timeout=20000)
                        send_btn.click()
                        time.sleep(3)
                        print(f"Sent to {num}")
                    except Exception as e:
                        print(f"Failed to send to {num}: {e}")
            
            browser.close()
            
        # 4. Mark orders as dispatched
        for order in orders_to_mark:
            order.whatsapp_dispatched = True
            
        db.session.commit()
        print(f"[{datetime.now()}] Dispatch cycle completed.")

if __name__ == "__main__":
    while True:
        try:
            run_dispatcher()
        except Exception as e:
            print(f"Dispatcher loop error: {e}")
        
        print("Waiting 5 minutes...")
        time.sleep(300)
