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

            # if specific_subsite_id:
            #     query = query.filter(Order.subsite_id == specific_subsite_id)
            
            # DEBUG: Print exact SQL and params
            print(f"[DEBUG-SQL] StoreID: {store.id}")
            # print(str(query.statement.compile(compile_kwargs={"literal_binds": True})))
            
            pending_orders = query.all()
            print(f"[DEBUG] Store {store.name}: Found {len(pending_orders)} orders (Force={force_resend})")
            
            if not pending_orders:
                return

            for order in pending_orders:
                orders_to_mark.add(order)
                
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
                # Check Auto-Send Flag (Global Subsite + Local Store)
                subsite_auto = getattr(subsite, 'auto_send_whatsapp', True)
                store_auto = getattr(s, 'auto_send_on_close', True)
                
                if subsite_auto and store_auto:
                    run_processing(s, subsite.id, force=False)
                else:
                    print(f"[Cycle] Skipping Auto-Dispatch for {s.name}. (Subsite: {subsite_auto}, Store: {store_auto})")
        
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
            
            login_selector = 'div[contenteditable="true"], [data-testid="chat-list"], #pane-side'
            try:
                page.wait_for_selector(login_selector, timeout=30000)
            except:
                print("Action Required: Please log in to WhatsApp Web.")
                page.wait_for_selector(login_selector, timeout=300000)

            for num, stores_dict in dispatches.items():
                for store_id, orders_data in stores_dict.items():
                    store = Store.query.get(store_id) # Reload store object safely
                    if not store: continue
                    
                    operations = [] # List of (text, [order_ids])

                    template_to_use = store.whatsapp_template
                    if not template_to_use or not template_to_use.strip():
                        template_to_use = (
                            "{saudacao}! Seguem os pedidos da rodada para a loja *{loja}*:\n\n"
                            "👤 *{cliente}* (Pedido #{id_pedido})\n"
                            "📍 Local: {endereco}\n"
                            "🛒 *Itens:*\n{itens}\n"
                            "💰 Total: {total}\n"
                            "💳 Pagamento: {pagamento}\n"
                            "----------------------------------------\n\n"
                            "📊 *RESUMO GERAL DOS PEDIDOS:*\n"
                            "{resumo_geral}\n\n"
                            "⚠️ Mensagem gerada automaticamente pelo centralizador Lanches OP, caso tenha algum apontamento, por favor, aguarde pois posso estar atuando na área, assim que possível retorno o contato."
                        )
                        
                    # Smart Template Parsing
                    tmpl_normalized = template_to_use.replace('\r\n', '\n')
                    if True:
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

                        # Calculate Total Por Área (matricial por setor)
                        sectors = set()
                        summary_matrix = {}
                        for order_id_iter, items_iter in orders_data.items():
                             order_obj = next((o for o in orders_to_mark if o.id == order_id_iter), None)
                             sector_name = order_obj.sector.name if (order_obj and order_obj.sector) else "N/A"
                                                    # Calculate Total Por Área (grouped by sector, no headers, <area> \n <item> <quantity>)
                        sector_items = {}
                        for order_id_iter, items_iter in orders_data.items():
                             order_obj = next((o for o in orders_to_mark if o.id == order_id_iter), None)
                             sector_name = order_obj.sector.name if (order_obj and order_obj.sector) else "N/A"
                             if sector_name not in sector_items:
                                 sector_items[sector_name] = {}
                             for it in items_iter:
                                 key = it['name']
                                 if it['subitems']: key += f" ({it['subitems']})"
                                 if key not in sector_items[sector_name]:
                                     sector_items[sector_name][key] = 0
                                 sector_items[sector_name][key] += it['quantity']
                        
                        sector_blocks = []
                        for sec_name, items_map in sorted(sector_items.items()):
                            block_lines = [sec_name]
                            for item_key, qty in sorted(items_map.items()):
                                block_lines.append(f"{item_key}\t{qty}")
                            sector_blocks.append("\n".join(block_lines))
                        total_por_area_str = "\n\n".join(sector_blocks)

                        # Calculate Resumo Geral (soma simples de itens)
                        batch_summary_items = {}
                        for order_id_iter, items_iter in orders_data.items():
                             for it in items_iter:
                                 key = it['name']
                                 if it['subitems']: key += f" ({it['subitems']})"
                                 
                                 if key not in batch_summary_items:
                                     batch_summary_items[key] = 0
                                 batch_summary_items[key] += it['quantity']
                        
                        resumo_geral_lines = []
                        for key, qty in sorted(batch_summary_items.items()):
                            resumo_geral_lines.append(f"{qty}x {key}")
                        resumo_geral_str = "\n".join(resumo_geral_lines)

                        # Global Vars Context
                        now_hour = datetime.now().hour
                        if 5 <= now_hour < 12: s_txt = "Bom dia"
                        elif 12 <= now_hour < 18: s_txt = "Boa tarde"
                        else: s_txt = "Boa noite"
                        saudacao = f"{s_txt}! Seguem os pedidos da rodada:"
                        
                        endereco_replan = (
                            "REPLAN - Refinaria Planalto de Paulínia, SP-332, Km 130 - s/n - Bonfim, Paulínia - SP, 13140-000\n\n"
                            "REPLAN - Portaria Sul"
                        )
                        
                        aviso_text = (
                            "⚠️ *Mensagem automática do Centralizador Lanches OP*\n\n"
                            "Caso eu não responda imediatamente, é possível que esteja em atendimento ou atuando na área. Assim que possível, retornarei o contato.\n\n"
                            "Também estamos cientes do acréscimo no valor do frete em razão da cobrança de pedágio.\n\n"
                            "Agradeço pela compreensão!"
                        )
                        
                        def replace_globals(txt):
                            t = txt.replace('{loja}', store.name)
                            t = t.replace('{saudacao}', saudacao)
                            t = t.replace('{resumo_geral}', resumo_geral_str)
                            t = t.replace('{total por área}', total_por_area_str)
                            t = t.replace('{endereco replan}', endereco_replan)
                            t = t.replace('{Aviso}', aviso_text)
                            return t

                        final_header = replace_globals(header_txt)
                        final_footer = replace_globals(footer_txt)

                        # Process Body Loop - Group orders by User Name to avoid duplication
                        current_batch_text = []
                        current_batch_ids = []
                        
                        sorted_orders = sorted(orders_data.items(), key=lambda x: x[0]) 
                        
                        print(f"[DEBUG] sorted_orders keys: {list(orders_data.keys())} (Types: {[type(k) for k in orders_data.keys()]})")
                        print(f"[DEBUG] orders_to_mark IDs: {[o.id for o in orders_to_mark]} (Types: {[type(o.id) for o in orders_to_mark]})")
                        
                        user_groups = {}
                        for order_id, items in sorted_orders:
                            order_obj = next((o for o in orders_to_mark if o.id == order_id), None)
                            if not order_obj:
                                print(f"[DEBUG] Skipping order_id {order_id} because it was not found in orders_to_mark!")
                                continue
                            
                            user_name = order_obj.user.name if order_obj.user else 'Cliente'
                            user_phone = order_obj.user.phone if order_obj.user else 'N/A'
                            addr = order_obj.sector.name if order_obj.sector else 'N/A'
                            
                            pay_method = "A Combinar"
                            if order_obj.pix_charge_id: pay_method = "Pix (Online)"
                            elif order_obj.payment_status == 'approved': pay_method = "Pago"
                            
                            if user_name not in user_groups:
                                user_groups[user_name] = {
                                    'items': [],
                                    'order_ids': [],
                                    'user_phone': user_phone,
                                    'address': addr,
                                    'total_val': 0.0,
                                    'pay_methods': set(),
                                    'created_at': order_obj.created_at
                                }
                            
                            user_groups[user_name]['items'].extend(items)
                            user_groups[user_name]['order_ids'].append(order_id)
                            user_groups[user_name]['pay_methods'].add(pay_method)
                            for it in items:
                                user_groups[user_name]['total_val'] += (float(it.get('price', 0)) * it['quantity'])

                        # Sort user groups chronologically by their first order ID
                        sorted_users = sorted(user_groups.items(), key=lambda x: x[1]['order_ids'][0])

                        for user_name, data in sorted_users:
                            # Aggregate Items
                            aggregated_items = {}
                            for it in data['items']:
                                key = it['name']
                                if it['subitems']: key += f" ({it['subitems']})"
                                if key not in aggregated_items:
                                    aggregated_items[key] = 0
                                aggregated_items[key] += it['quantity']
                                
                            items_str = f"{user_name}\n"
                            items_inline_list = []
                            for key, qty in sorted(aggregated_items.items()):
                                items_str += f"\t{key}\t{qty}\n"
                                items_inline_list.append(f"{qty}x {key}")
                            items_str = items_str.rstrip('\n')
                            items_inline_str = " - ".join(items_inline_list)
                            
                            pay_method_str = ", ".join(sorted(list(data['pay_methods'])))
                            
                            # Replace Row Vars
                            row_txt = body_tmpl
                            replacements = {
                                '{id_pedido}': ", ".join(map(str, data['order_ids'])),
                                '{data}': data['created_at'].strftime('%d/%m %H:%M'),
                                '{itens}': items_str,
                                '{itens_inline}': items_inline_str,
                                '{total}': f"R$ {data['total_val']:.2f}",
                                '{cliente}': user_name,
                                '{telefone}': data['user_phone'],
                                '{endereco}': data['address'],
                                '{pagamento}': pay_method_str,
                                '{observacao}': "N/A",
                                '{loja}': store.name,
                                '{saudacao}': saudacao
                            }
                            
                            for k, v in replacements.items():
                                row_txt = row_txt.replace(k, v)
                            
                            current_batch_text.append(row_txt)
                            current_batch_ids.extend(data['order_ids'])
                        
                        if current_batch_text:
                            # Assemble Final Message
                            body_block = "\n\n".join(current_batch_text)
                            
                            parts = []
                            if final_header.strip(): parts.append(final_header)
                            if body_block.strip(): parts.append(body_block)
                            if final_footer.strip(): parts.append(final_footer)
                            
                            final_msg = "\n".join(parts)
                            if final_msg.strip():
                                operations.append((final_msg, current_batch_ids))

                    # Execute Operations
                    print(f"[DEBUG] operations count to send: {len(operations)}")
                    for text, associated_ids in operations:
                        print(f"Sending to {store.name} ({num})...")
                        try:
                            # 1. Open Chat
                            page.goto(f"https://web.whatsapp.com/send?phone={num}")
                            
                            # 2. Wait for input box
                            inp_selector = 'footer div[contenteditable="true"]'
                            try:
                                page.wait_for_selector(inp_selector, timeout=20000)
                            except:
                                # Fallback selectors
                                try:
                                    inp_selector = 'div[contenteditable="true"][data-tab="10"]'
                                    page.wait_for_selector(inp_selector, timeout=10000)
                                except:
                                    inp_selector = 'div[role="textbox"]'
                                    page.wait_for_selector(inp_selector, timeout=10000)

                            time.sleep(1) # Stability
                            
                            # 3. Focus and Fill message
                            page.focus(inp_selector)
                            page.fill(inp_selector, text)
                            time.sleep(0.5)
                            
                            # 4. Press Enter
                            page.keyboard.press("Enter")
                            
                            # 5. Fallback: Click the Send Button if visible
                            time.sleep(1.5)
                            try:
                                send_btn = page.locator('span[data-testid="send"], button[data-testid="compose-btn-send"], [data-icon="send"]').first
                                if send_btn.is_visible():
                                    send_btn.click()
                                    time.sleep(1)
                            except:
                                pass
                                
                            time.sleep(6) # Delay to ensure transmission

                            print(f"Sent to {num}")
                            
                            # Mark success
                            for oid in associated_ids:
                                found = next((o for o in orders_to_mark if o.id == oid), None)
                                if found: found.whatsapp_dispatched = True
                                    
                        except Exception as e:
                            print(f"Failed to send to {num}: {e}")
            
            time.sleep(5) # Give WhatsApp Web extra time to synchronize outbox
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
