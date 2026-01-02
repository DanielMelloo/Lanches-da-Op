import os

import time
import json
import urllib.parse
from datetime import datetime

# Override DB config to point to SSH Tunnel (Production)
os.environ['DB_HOST'] = '127.0.0.1:3307'
os.environ['DB_USER'] = 'root'
os.environ['DB_PASSWORD'] = 'CodeEz4ever'
os.environ['DB_NAME'] = 'lanches_da_op'
# Prevent scheduler from starting in this worker process
os.environ['SKIP_SCHEDULER'] = 'true'
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
        db.session.remove() # Ensure fresh data for this cycle
        
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

        import re
        
        # Helper to process a store's pending orders
        def process_store_orders(store, specific_subsite_id=None, force_resend=False):
            if not store.whatsapp_number:
                return
            
            # Strict Sanitization
            num = re.sub(r'\D', '', store.whatsapp_number)
            if not num: return
            if len(num) in [10, 11]: num = '55' + num
            
            # Query logic
            query = Order.query.join(OrderItem).join(Item).filter(Item.store_id == store.id)
            
            if not force_resend:
                query = query.filter(Order.whatsapp_dispatched == False)
            else:
                today = datetime.now().date()
                query = query.filter(db.func.date(Order.created_at) == today)
                print(f"[DEBUG] Force resend for {store.name} on date {today}")

            if specific_subsite_id:
                query = query.filter(Order.subsite_id == specific_subsite_id)
            
            pending_orders = query.all()
            print(f"[DEBUG] Store {store.name}: Found {len(pending_orders)} orders (Force={force_resend})")
            
            if not pending_orders:
                return

            for order in pending_orders:
                orders_to_mark.add(order)
                
                # Construct items list for the current order
                # Construct items list for the current order
                items_for_order = []
                # Only items for THIS store
                relevant_items = [oi for oi in order.order_items if oi.item and oi.item.store_id == store.id]
                
                for oi in relevant_items:
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

                    item_data = {
                        'name': oi.item.name,
                        'quantity': oi.quantity,
                        'price': oi.price_at_moment,
                        'subitems': subtext
                    }
                    items_for_order.append(item_data)

                # Sanitize Number
                clean_num = re.sub(r'\D', '', store.whatsapp_number)
                if len(clean_num) in [10, 11]: clean_num = '55' + clean_num
                
                if clean_num not in dispatches: dispatches[clean_num] = {}
                if store.id not in dispatches[clean_num]: dispatches[clean_num][store.id] = {}
                dispatches[clean_num][store.id][order.id] = items_for_order

        processed_stores_in_cycle = set()

        # Helper to avoid duplicates
        def run_processing(store_obj, subsite_id=None, force=False):
            if store_obj.id in processed_stores_in_cycle: return
            process_store_orders(store_obj, subsite_id, force)
            processed_stores_in_cycle.add(store_obj.id)

        # Process closed subsites
        for subsite in closed_subsites:
            subsite_stores = Store.query.filter_by(subsite_id=subsite.id).all()
            for s in subsite_stores:
                run_processing(s, subsite.id, force_resend=False)
        
        # Process manual triggers
        for s in manual_stores:
            print(f"[{datetime.now()}] Manual dispatch detected for: {s.name} (Resending Today's Orders)")
            # If it was already processed as closed, we might need to RE-process with force=True?
            # actually, if it was closed, it only sent 'Not Dispatched'. 
            # If user wants Force Resend, we should ensure we get ALL orders.
            # So if it's in processed_stores_in_cycle, we might need to clear its entry and re-run?
            # Simpler: Checks manual FIRST? 
            # No, manual is usually the override.
            
            # If already processed (e.g. standard close), we might miss "Dispatched" orders if we don't force.
            # Let's remove from dispatches first if re-processing.
            num = re.sub(r'\D', '', s.whatsapp_number) if s.whatsapp_number else None
            if num and len(num) in [10, 11]: num = '55' + num
            if num and num in dispatches and s.id in dispatches[num]:
                 del dispatches[num][s.id]
            
            run_processing(s, force=True)
            processed_stores_in_cycle.add(s.id)
            
            s.pending_manual_dispatch = False
            
            # Check if this store generated any dispatch
            num = re.sub(r'\D', '', s.whatsapp_number) if s.whatsapp_number else None
            if num and len(num) in [10, 11]: num = '55' + num
            
            if num and (num not in dispatches or s.id not in dispatches[num]):
                 print(f" -> No pending orders found for {s.name}.")

        if not dispatches:
            # print(f"[{datetime.now()}] Nothing to dispatch. Skipping.") # Too spammy for 15s interval
            db.session.commit() # Flush manual flags
            return

        # 3. Send via WhatsApp Web (Playwright)
        # Use absolute path based on script location for reliability
        script_dir = os.path.dirname(os.path.abspath(__file__))
        user_data_dir = os.path.join(script_dir, "whatsapp_session")
        
        
        with sync_playwright() as p:
            browser = p.chromium.launch_persistent_context(
                user_data_dir,
                headless=False,
                args=['--no-sandbox']
            )
            page = browser.pages[0] if browser.pages else browser.new_page()
            print("Opening WhatsApp Web...")
            page.goto("https://web.whatsapp.com/")
            
            try:
                page.wait_for_selector('div[contenteditable="true"]', timeout=30000)
            except:
                print("Action Required: Please log in to WhatsApp Web.")
                page.wait_for_selector('div[contenteditable="true"]', timeout=300000)

            for num, stores_dict in dispatches.items():
                for store_id, orders_data in stores_dict.items():
                    store = Store.query.get(store_id) # Reload store object safely
                    if not store: continue
                    
                    operations = [] # List of (text, [order_ids])

                    if store.whatsapp_template and store.whatsapp_template.strip():
                        # Smart Template Parsing
                        tmpl_normalized = store.whatsapp_template.replace('\r\n', '\n')
                        full_tmpl_lines = tmpl_normalized.split('\n')
                        
                        row_vars = ['{id_pedido}', '{cliente}', '{telefone}', '{endereco}', 
                                    '{pagamento}', '{data}', '{itens}', '{itens_inline}', 
                                    '{total}', '{observacao}']
                        
                        first_row_idx = -1
                        last_row_idx = -1
                        
                        for i, line in enumerate(full_tmpl_lines):
                            if any(v in line for v in row_vars):
                                if first_row_idx == -1: first_row_idx = i
                                last_row_idx = i
                        
                        if first_row_idx == -1:
                            header_lines = []
                            body_lines = full_tmpl_lines
                            footer_lines = []
                        else:
                            header_lines = full_tmpl_lines[:first_row_idx]
                            body_lines = full_tmpl_lines[first_row_idx : last_row_idx+1]
                            footer_lines = full_tmpl_lines[last_row_idx+1:]

                        header_txt = "\n".join(header_lines)
                        body_tmpl = "\n".join(body_lines)
                        footer_txt = "\n".join(footer_lines)

                        # Calculate Batch Summary (Resumo Geral)
                        batch_summary_items = {}
                        for order_id_iter, items_iter in orders_data.items():
                             # Check if order is valid (skip if not in fetch list? No, orders_data is source of truth)
                             for it in items_iter:
                                 key = it['name']
                                 if it['subitems']: key += f" ({it['subitems']})"
                                 
                                 if key not in batch_summary_items:
                                     batch_summary_items[key] = 0
                                 batch_summary_items[key] += it['quantity']
                        
                        batch_summary_lines = []
                        for key, qty in batch_summary_items.items():
                            batch_summary_lines.append(f"{qty}x {key}")
                        batch_summary_str = "\n".join(batch_summary_lines)

                        # Global Vars Context
                        now_hour = datetime.now().hour
                        if 5 <= now_hour < 12: saudacao = "Bom dia"
                        elif 12 <= now_hour < 18: saudacao = "Boa tarde"
                        else: saudacao = "Boa noite"
                        
                        def replace_globals(txt):
                            t = txt.replace('{loja}', store.name)
                            t = t.replace('{saudacao}', saudacao)
                            t = t.replace('{resumo_geral}', batch_summary_str)
                            return t

                        final_header = replace_globals(header_txt)
                        final_footer = replace_globals(footer_txt)

                        # Process Body Loop
                        current_batch_text = []
                        current_batch_ids = []
                        
                        sorted_orders = sorted(orders_data.items(), key=lambda x: x[0]) 
                        
                        for order_id, items in sorted_orders:
                            order_obj = next((o for o in orders_to_mark if o.id == order_id), None)
                            if not order_obj: continue

                            # Aggregate Items
                            aggregated_items = {}
                            total_val = 0.0
                            for it in items:
                                key = it['name']
                                if it['subitems']: key += f" ({it['subitems']})"
                                if key not in aggregated_items:
                                    aggregated_items[key] = {'qt': 0, 'price': float(it.get('price', 0))}
                                aggregated_items[key]['qt'] += it['quantity']
                                total_val += (float(it.get('price', 0)) * it['quantity'])

                            items_str = ""
                            items_inline_list = []
                            for key, data in aggregated_items.items():
                                qt = data['qt']
                                items_str += f"- {qt}x {key}\n"
                                items_inline_list.append(f"{qt}x {key}")
                            items_inline_str = " - ".join(items_inline_list)

                            # Attributes
                            addr = order_obj.sector.name if order_obj.sector else "N/A"
                            obs = "N/A" # Placeholder
                            user_name = order_obj.user.name if order_obj.user else 'Cliente'
                            user_phone = order_obj.user.phone if order_obj.user else 'N/A'
                            
                            pay_method = "A Combinar"
                            if order_obj.pix_charge_id: pay_method = "Pix (Online)"
                            elif order_obj.payment_status == 'approved': pay_method = "Pago"

                            # Replace Row Vars
                            row_txt = body_tmpl
                            # Attributes mapping
                            replacements = {
                                '{id_pedido}': str(order_id),
                                '{data}': order_obj.created_at.strftime('%d/%m %H:%M'),
                                '{itens}': items_str,
                                '{itens_inline}': items_inline_str,
                                '{total}': f"R$ {total_val:.2f}",
                                '{cliente}': user_name,
                                '{telefone}': user_phone,
                                '{endereco}': addr,
                                '{pagamento}': pay_method,
                                '{observacao}': obs,
                                # Also allow globals in body if needed
                                '{loja}': store.name,
                                '{saudacao}': saudacao
                            }
                            
                            for k, v in replacements.items():
                                row_txt = row_txt.replace(k, v)
                            
                            current_batch_text.append(row_txt)
                            current_batch_ids.append(order_id)
                        
                        if current_batch_text:
                            # Assemble Final Message
                            # Use newlines to separate header, body items, footer
                            body_block = "\n".join(current_batch_text)
                            
                            parts = []
                            if final_header.strip(): parts.append(final_header)
                            if body_block.strip(): parts.append(body_block)
                            if final_footer.strip(): parts.append(final_footer)
                            
                            final_msg = "\n".join(parts) # or \n\n if preferred spacing
                            if final_msg.strip():
                                operations.append((final_msg, current_batch_ids))

                    # Execute Operations
                    for text, associated_ids in operations:
                        print(f"Sending to {store.name} ({num})...")
                        try:
                            # 1. Open Chat
                            page.goto(f"https://web.whatsapp.com/send?phone={num}")
                            
                            # 2. Wait for input box
                            inp_selector = 'div[contenteditable="true"][data-tab="10"]'
                            try:
                                page.wait_for_selector(inp_selector, timeout=20000)
                            except:
                                # Fallback selector
                                inp_selector = 'div[contenteditable="true"]'
                                page.wait_for_selector(inp_selector, timeout=20000)

                            time.sleep(1) # Stability
                            
                            # 3. Type message (fill is faster/safer than type for long text)
                            # We might need to handle line breaks. fill() usually handles \n well in contenteditable.
                            page.fill(inp_selector, text)
                            time.sleep(0.5)
                            
                            # 4. Press Enter
                            page.keyboard.press("Enter")
                            
                            try:
                                # Optional: Backup click if Enter didn't work (wait 2s to see if sent)
                                # Check if text is still there? 
                                # Simpler: Just wait a bit.
                                time.sleep(2)
                            except:
                                pass

                            print(f"Sent to {num}")
                            
                            # Mark success
                            for oid in associated_ids:
                                found = next((o for o in orders_to_mark if o.id == oid), None)
                                if found: found.whatsapp_dispatched = True
                                    
                        except Exception as e:
                            print(f"Failed to send to {num}: {e}")
            
            browser.close()
            
        # Commit tracking changes (successful ones only)
        db.session.commit()
        print(f"[{datetime.now()}] Dispatch cycle completed.")

if __name__ == "__main__":
    print("--- WhatsApp Dispatcher Started (Polling every 15s) ---")
    while True:
        try:
            run_dispatcher()
        except Exception as e:
            print(f"Dispatcher loop error: {e}")
        
        # Reduced wait time for responsiveness
        time.sleep(15)
