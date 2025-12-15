from flask import Blueprint, render_template, redirect, url_for, request, session, flash, current_app
from flask_login import login_required, current_user
from models import Subsite, Item, Sector, Order, OrderItem, Status, Store
from database import db
import json

user_bp = Blueprint('user', __name__, url_prefix='/user')

@user_bp.route('/dashboard')
@login_required
def dashboard():
    # Performance Optimization: Don't check payments or load heavy data here.
    # The frontend will fetch data via AJAX (Skeleton Loading).
    subsites = Subsite.query.filter_by(active=True).all()
    return render_template('user_dashboard.html', subsites=subsites)

@user_bp.route('/api/dashboard/orders')
@login_required
def api_dashboard_orders():
    # Fetch recent 5 orders for dashboard
    orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).limit(5).all()
    return render_template('partials/order_list_dashboard.html', orders=orders)

@user_bp.route('/subsite/<int:subsite_id>/menu')
@login_required
def menu(subsite_id):
    from models import Store
    subsite = Subsite.query.get_or_404(subsite_id)
    
    # Query items through Store relationship
    menu_items = Item.query.join(Store).filter(
        Store.subsite_id == subsite_id,
        Item.active == True
    ).all()
    
    cart = session.get('cart', {})
    
    # Find last order for this subsite to offer "reorder"
    last_order = Order.query.filter_by(
        user_id=current_user.id,
        subsite_id=subsite_id
    ).order_by(Order.created_at.desc()).first()
    
    return render_template('user_menu.html', subsite=subsite, items=menu_items, cart=cart, last_order=last_order)

@user_bp.route('/item/<int:item_id>/detail')
@login_required
def item_detail(item_id):
    item = Item.query.get_or_404(item_id)
    subsite_id = request.args.get('subsite_id', type=int)
    return render_template('user_item_detail.html', item=item, subsite_id=subsite_id)

@user_bp.route('/cart/add', methods=['POST'])
@login_required
def add_to_cart():
    import json
    item_id = request.form.get('item_id')
    qty = int(request.form.get('quantity', 1))
    subsite_id = int(request.form.get('subsite_id'))
    subitems_choice = request.form.get('subitems_choice', '').strip()
    
    # Per-subsite cart structure: {'subsite_id': {item_id: {qty, subitems}, ...}}
    cart = session.get('cart', {})
    subsite_cart = cart.get(str(subsite_id), {})
    
    # Parse subitems if present
    subitems_data = None
    if subitems_choice:
        try:
            subitems_data = json.loads(subitems_choice)
        except:
            pass
    
    # Store item with subitems
    current_qty = subsite_cart.get(item_id, {}).get('qty', 0) if isinstance(subsite_cart.get(item_id), dict) else subsite_cart.get(item_id, 0)
    
    subsite_cart[item_id] = {
        'qty': current_qty + qty,
        'subitems': subitems_data
    }
    
    cart[str(subsite_id)] = subsite_cart
    session['cart'] = cart
    session.modified = True
    
    flash('Item adicionado!', 'success')
    return redirect(url_for('user.menu', subsite_id=subsite_id))

@user_bp.route('/reorder/<int:order_id>', methods=['POST'])
@login_required
def reorder(order_id):
    """Add all items from a previous order to the cart"""
    order = Order.query.get_or_404(order_id)
    
    # Security check
    if order.user_id != current_user.id:
        return {'success': False, 'message': 'Acesso negado'}, 403
    
    cart = session.get('cart', {})
    subsite_cart = cart.get(str(order.subsite_id), {})
    
    # Add each item from order
    for order_item in order.order_items:
        item_id_str = str(order_item.item_id)
        subsite_cart[item_id_str] = {
            'qty': order_item.quantity,
            'subitems': order_item.subitems_json or []
        }
    
    cart[str(order.subsite_id)] = subsite_cart
    session['cart'] = cart
    session.modified = True
    
    return {'success': True}

@user_bp.route('/cart/remove', methods=['POST'])
@login_required
def remove_from_cart():
    item_id = request.form.get('item_id')
    subsite_id = request.form.get('subsite_id')
    
    cart = session.get('cart', {})
    if str(subsite_id) in cart and item_id in cart[str(subsite_id)]:
        del cart[str(subsite_id)][item_id]
        session['cart'] = cart
        session.modified = True
        flash('Item removido do carrinho.', 'success')
    
    return redirect(url_for('user.checkout', subsite_id=subsite_id))

@user_bp.route('/cart/update', methods=['POST'])
@login_required
def update_cart():
    item_id = request.form.get('item_id')
    qty = int(request.form.get('quantity', 1))
    subsite_id = request.form.get('subsite_id')
    
    cart = session.get('cart', {})
    if str(subsite_id) in cart:
        if qty > 0:
            # Preserve subitems if they exist
            if isinstance(cart[str(subsite_id)].get(item_id), dict):
                cart[str(subsite_id)][item_id]['qty'] = qty
            else:
                cart[str(subsite_id)][item_id] = qty
        else:
            cart[str(subsite_id)].pop(item_id, None)
        session['cart'] = cart
        session.modified = True
    
    return redirect(url_for('user.checkout', subsite_id=subsite_id))

@user_bp.route('/cart/clear')
@login_required
def clear_cart():
    subsite_id = request.args.get('subsite_id')
    cart = session.get('cart', {})
    if subsite_id and str(subsite_id) in cart:
        del cart[str(subsite_id)]
    else:
        cart = {}
    session['cart'] = cart
    return redirect(url_for('user.dashboard'))

@user_bp.route('/cart/edit/<int:item_id>')
@login_required
def edit_cart_item(item_id):
    subsite_id = request.args.get('subsite_id')
    if not subsite_id:
        flash('Subsite não especificado.', 'error')
        return redirect(url_for('user.dashboard'))
        
    cart = session.get('cart', {})
    subsite_cart = cart.get(str(subsite_id), {})
    
    # Handle int vs dict structure
    cart_data = subsite_cart.get(str(item_id)) # try string key
    if not cart_data:
        cart_data = subsite_cart.get(item_id) # try int key
        
    if not cart_data:
        flash('Item não encontrado no carrinho.', 'error')
        return redirect(url_for('user.checkout', subsite_id=subsite_id))
        
    item = Item.query.get_or_404(item_id)
    
    existing_qty = 1
    existing_subitems = []
    
    if isinstance(cart_data, dict):
        existing_qty = cart_data.get('qty', 1)
        existing_subitems = cart_data.get('subitems', [])
    else:
        existing_qty = cart_data
        
    return render_template('user_item_detail.html', 
                           item=item, 
                           subsite_id=subsite_id, 
                           edit_mode=True,
                           existing_qty=existing_qty,
                           existing_subitems=existing_subitems)

@user_bp.route('/meus-pedidos')
@login_required
def orders():
    # Render the shell with skeletons. Data fetched via API.
    return render_template('user_orders.html')

@user_bp.route('/api/orders')
@login_required
def api_orders():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    filter_status = request.args.get('filter', 'all')
    
    query = Order.query.filter_by(user_id=current_user.id)
    
    if filter_status == 'pending':
        query = query.join(Status).filter(Status.name.in_(['Pagamento Pendente', 'Pendente', 'Novo']))
    elif filter_status == 'completed':
        query = query.join(Status).filter(Status.name.in_(['Pagamento Confirmado', 'Concluido', 'Entregue', 'Enviado']))
        
    pagination = query.order_by(Order.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    
    return render_template('partials/order_list_items.html', orders=pagination.items, pagination=pagination, filter_status=filter_status)

@user_bp.route('/pedido/<int:order_id>')
@login_required
def order_detail(order_id):
    order = Order.query.get_or_404(order_id)
    if order.user_id != current_user.id:
        flash('Acesso negado.', 'error')
        return redirect(url_for('user.orders'))
        
    # Single Verification on View (Keep this for detail view as it's critical)
    if order.payment_status == 'pending' and order.pix_charge_id:
        check_single_order_payment(order)
        
    return render_template('user_order_detail.html', order=order)

def check_pending_payments(user):
    """Checks EFí API for all pending PIX orders of this user."""
    pending_orders = Order.query.filter_by(user_id=user.id, payment_status='pending').all()
    if not pending_orders: return

    from services.efi_service import EfiService
    service = EfiService()
    
    updated_count = 0
    for order in pending_orders:
        if not order.pix_charge_id: continue
        
        status_efi = service.check_status(order.subsite, order.pix_charge_id)
        if status_efi == 'CONCLUIDA':
             # Update to Paid
             paid_status = Status.query.filter_by(name='Pagamento Confirmado').first()
             if not paid_status:
                 # Fallback if specific status not found
                 paid_status = order.status 
             
             order.status = paid_status
             order.payment_status = 'approved'
             updated_count += 1
    
    if updated_count > 0:
        db.session.commit()
        flash(f'{updated_count} pagamento(s) confirmado(s)!', 'success')

def check_single_order_payment(order):
    from services.efi_service import EfiService
    service = EfiService()
    status_efi = service.check_status(order.subsite, order.pix_charge_id)
    
    if status_efi == 'CONCLUIDA':
         paid_status = Status.query.filter_by(name='Pagamento Confirmado').first()
         if paid_status:
             order.status = paid_status
         order.payment_status = 'approved'
         db.session.commit()
         return True
    return False

@user_bp.route('/api/check-payment/<int:order_id>')
@login_required
def check_payment_status(order_id):
    order = Order.query.get_or_404(order_id)
    if order.user_id != current_user.id:
        return {'error': 'Unauthorized'}, 403
    
    if order.payment_status == 'approved':
        return {'paid': True, 'status': order.status.name}

    if order.payment_status == 'pending' and order.pix_charge_id:
        is_paid = check_single_order_payment(order)
        if is_paid:
            return {'paid': True, 'status': order.status.name}
            
    return {'paid': False, 'status': order.status.name}

@user_bp.route('/checkout/<int:subsite_id>', methods=['GET', 'POST'])
@login_required
def checkout(subsite_id):
    subsite = Subsite.query.get_or_404(subsite_id)
    cart = session.get('cart', {})
    subsite_cart = cart.get(str(subsite_id), {})
    
    if not subsite_cart:
        flash('Carrinho vazio.', 'warning')
        return redirect(url_for('user.menu', subsite_id=subsite_id))
        
    items_in_cart = []
    total_items = 0.0
    
    # Fetch items details - handle both old (int) and new (dict) cart structure
    for item_id, cart_data in subsite_cart.items():
        item = Item.query.get(item_id)
        if item:
            # Handle both structures: old (qty as int) and new (dict with qty and subitems)
            if isinstance(cart_data, dict):
                qty = cart_data.get('qty', 1)
                subitems = cart_data.get('subitems', None)
            else:
                qty = cart_data
                subitems = None
            
            subtotal = item.price * qty
            
            # Add subitems prices
            if subitems:
                for group in subitems:
                    if group.get('type') == 'radio':
                        subtotal += group.get('price', 0) * qty
                    elif group.get('type') == 'checkbox':
                        for option in group.get('options', []):
                            subtotal += option.get('price', 0) * option.get('qty', 1) * qty
            
            total_items += subtotal
            items_in_cart.append({
                'item': item,
                'qty': qty,
                'subitems': subitems,
                'subtotal': subtotal
            })
    
    # Calculate Tax based on mode
    tax_value = 0.0
    if subsite.tax_mode == 'variable':
        tax_value = subsite.calculated_variable_tax or 0.0
    else:
        tax_value = subsite.fixed_tax_value or 0.0
        
    total_with_tax = total_items + tax_value

    # Apply 1.3% Markup if "Repassar Taxa Pix" is enabled
    markup = 1.013 if subsite.pass_pix_tax else 1.0
    total_general = total_with_tax * markup
    
    service_fee = total_general - total_items
            
    # Validating the calculation logic:
    # Total General = (Total Items + Tax) * Markup
    pass
    
    if request.method == 'POST':
        sector_id = request.form.get('sector_id')
        
        # Determine initial status based on payment requirement
        if subsite.require_payment:
            # Payment required → start as Pagamento Pendente
            initial_status = Status.query.filter_by(name='Pagamento Pendente').first()
        else:
            # No payment required → start as Pedido Confirmado
            initial_status = Status.query.filter_by(name='Pedido Confirmado').first()
        
        # Fallback to first status if named statuses don't exist
        if not initial_status:
            initial_status = Status.query.first()
        
        if not initial_status:
            flash('Erro: Nenhum status configurado no sistema.', 'error')
            return redirect(url_for('user.menu', subsite_id=subsite_id))

        if not sector_id:
             flash('Por favor, selecione um local de entrega.', 'error')
             return redirect(url_for('user.checkout', subsite_id=subsite_id))

        
        new_order = Order(
            user_id=current_user.id,
            subsite_id=subsite_id,
            sector_id=sector_id,
            status_id=initial_status.id,
            total_items=total_items,
            tax_fixed=tax_value, # Storing the calculated tax (fixed or variable) here
            service_fee=service_fee,
            total_general=total_general,
            payment_required=subsite.require_payment
        )
        db.session.add(new_order)
        db.session.flush()
        
        for cart_item in items_in_cart:
            order_item = OrderItem(
                order_id=new_order.id,
                item_id=cart_item['item'].id,
                quantity=cart_item['qty'],
                price_at_moment=cart_item['item'].price,
                subtotal=cart_item['subtotal'],
                subitems_json=cart_item['subitems']
            )
            db.session.add(order_item)

        db.session.commit()
        
        # ------------------------------------------------------------------
        # PAYMENT INTEGRATION (EFí)
        # ------------------------------------------------------------------
        if subsite.require_payment:
            try:
                db.session.refresh(new_order) # Ensure relationships are loaded
                
                from services.efi_service import EfiService
                service = EfiService()
                
                # Log attempt
                try:
                    with open('payment_debug.log', 'a', encoding='utf-8') as f:
                        f.write(f"Attempting charge for Order {new_order.id}\n")
                except Exception as log_err:
                     print(f"Log Error: {log_err}")
                
                charge_data = service.create_charge(new_order)
                
                if charge_data:
                    new_order.pix_charge_id = charge_data.get('txid')
                    new_order.pix_code_copy_paste = charge_data.get('pixCopiaECola')
                    db.session.commit()
                    flash(f'Pedido realizado! Pagamento PIX gerado.', 'success')
                else:
                    flash(f'Pedido realizado, mas houve erro ao gerar o PIX. Tente novamente em "Meus Pedidos".', 'warning')
            except Exception as e:
                import traceback
                error_msg = f"{str(e)}\n{traceback.format_exc()}"
                print(f"Checkout Payment Error: {error_msg}")
                try:
                    with open('payment_debug.log', 'a', encoding='utf-8') as f:
                        f.write(f"ERROR Order {new_order.id}: {error_msg}\n")
                except:
                    pass
                flash(f'Erro no Pagamento: {str(e)}', 'warning')
        else:
            flash(f'Pedido realizado com sucesso!', 'success')
            
        if subsite.tax_mode == 'variable':
             from services.tax_service import recalculate_taxes
             recalculate_taxes(subsite_id)

        # Clear cart
        session.pop('cart', None)
        
        return redirect(url_for('user.order_detail', order_id=new_order.id))

    sectors = Sector.query.filter(
        ((Sector.subsite_id == subsite_id) | (Sector.subsite_id == None)) & 
        (Sector.active == True) & 
        ((Sector.type == 'location') | (Sector.type == None)) # Handle legacy/null as location
    ).all()
    
    return render_template('user_checkout.html', 
                           subsite=subsite, 
                           items=items_in_cart, 
                           total_items=total_items, 
                           total_general=total_general,
                           total_with_tax=total_with_tax,
                           service_fee=service_fee,
                           sectors=sectors)

@user_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        name = request.form.get('name')
        phone = request.form.get('phone')
        petro_key = request.form.get('petro_key').upper()
        
        if not petro_key or len(petro_key) != 4 or not petro_key.isalnum():
             flash('Chave deve ter 4 caracteres alfanuméricos.', 'error')
             return redirect(url_for('user.profile'))
             
        # Check uniqueness if changed
        if petro_key != current_user.petro_key:
             from models import User
             existing = User.query.filter_by(petro_key=petro_key).first()
             if existing:
                 flash('Esta chave já está em uso por outro usuário.', 'error')
                 return redirect(url_for('user.profile'))
        
        # Validate Phone
        clean_phone = ''.join(filter(str.isdigit, phone)) if phone else ''
        if phone and (len(clean_phone) < 10 or len(clean_phone) > 11):
             flash('Telefone inválido. Use (DD) 9XXXX-XXXX', 'error')
             return redirect(url_for('user.profile'))

        current_user.name = name
        current_user.phone = phone
        current_user.petro_key = petro_key
        db.session.commit()
        
        flash('Perfil atualizado com sucesso!', 'success')
        return redirect(url_for('user.profile'))
        
    return render_template('user_profile.html')
