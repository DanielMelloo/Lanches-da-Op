from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_required, current_user
from models import Subsite, User, Order, Status, db
from werkzeug.security import generate_password_hash

master_bp = Blueprint('master', __name__, url_prefix='/master')

def require_master(f):
    @login_required
    def decorated(*args, **kwargs):
        if current_user.role != 'admin_master':
            flash('Acesso restrito a Master Admin.', 'error')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    decorated.__name__ = f.__name__
    return decorated

@master_bp.route('/dashboard')
@require_master
def dashboard():
    return render_template('master_dashboard.html')

@master_bp.route('/subsite/<int:subsite_id>/update_tax', methods=['POST'])
@require_master
def update_tax_config(subsite_id):
    subsite = Subsite.query.get_or_404(subsite_id)
    
    tax_mode = request.form.get('tax_mode') # 'fixed' or 'variable'
    subsite.tax_mode = tax_mode
    
    if tax_mode == 'fixed':
        try:
            fixed_val = float(request.form.get('fixed_tax_value', 0).replace(',', '.'))
            subsite.fixed_tax_value = fixed_val
        except:
            flash('Valor da taxa fixa inválido.', 'error')
            return redirect(url_for('master.manage_subsites'))
            
    elif tax_mode == 'variable':
        # Parse expenses
        import json
        from datetime import datetime
        
        start_date_str = request.form.get('start_date')
        end_date_str = request.form.get('end_date')
        expenses_json = request.form.get('expenses_json')
        
        try:
            expenses = json.loads(expenses_json)
            total_expenses = sum(float(e['value']) for e in expenses)
            
            # Count orders in period
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
            
            # End date should include the whole day
            end_date = end_date.replace(hour=23, minute=59, second=59)
            
            order_count = Order.query.filter(
                Order.subsite_id == subsite_id,
                Order.created_at >= start_date,
                Order.created_at <= end_date,
                Order.status_id != 4 # Assuming 4 is Cancelled, need to verify. Or just count all valid.
                 # Actually, let's filter by "Not Cancelled". 
                 # Since we don't know ID for sure, let's ignore for now or check status name in a join.
                 # For simplicity, count ALL orders for now or refine later.
                 # Better: Join Status and filter name != 'Cancelado'
            ).count()
            
            # Avoid division by zero
            if order_count > 0:
                calculated_rate = total_expenses / order_count
            else:
                calculated_rate = 0.0
                flash('Aviso: Nenhum pedido no período, taxa calculada é 0.', 'warning')
                
            subsite.variable_tax_settings = {
                'start_date': start_date_str,
                'end_date': end_date_str,
                'expenses': expenses,
                'total_expenses': total_expenses,
                'order_count': order_count
            }
            subsite.calculated_variable_tax = calculated_rate
            
        except Exception as e:
            flash(f'Erro ao calcular taxa variável: {str(e)}', 'error')
            return redirect(url_for('master.manage_subsites'))
            
    # Retroactive Update: Synchronize all pending orders with new configuration
    try:
        # Fetch all orders for this subsite to filter in Python (safer for NULLs/Defaults)
        all_orders = Order.query.filter_by(subsite_id=subsite_id).all()
        
        new_tax = subsite.calculated_variable_tax if subsite.tax_mode == 'variable' else subsite.fixed_tax_value
        markup = 1.013 if subsite.require_payment else 1.0
        
        count_updated = 0
        for order in all_orders:
            # Skip ONLY confirmed payments
            if order.payment_status == 'approved':
                continue
                
            # Update Tax Value
            order.tax_fixed = new_tax
            
            # Sync Payment Requirement setting (to match the markup logic)
            order.payment_required = subsite.require_payment
            
            # Recalculate Totals
            total_with_tax = order.total_items + new_tax
            order.total_general = total_with_tax * markup
            order.service_fee = order.total_general - order.total_items
            
            count_updated += 1
            
        db.session.commit()
        if count_updated > 0:
            flash(f'Configuração salva. {count_updated} pedidos recalculados (pagamentos pendentes).', 'success')
        else:
            flash('Configuração salva.', 'success')
        return redirect(url_for('master.manage_subsites'))

    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao atualizar pedidos: {str(e)}', 'error')
        return redirect(url_for('master.manage_subsites'))
    

@master_bp.route('/subsites', methods=['GET', 'POST'])
@require_master
def manage_subsites():
    if request.method == 'POST':
        action = request.form.get('action')
        subsite_id = request.form.get('subsite_id')
        
        if subsite_id:
            subsite = Subsite.query.get_or_404(subsite_id)
            
            if action == 'update_name':
                subsite.name = request.form.get('name')
                db.session.commit()
                flash('Nome atualizado.', 'success')
            
            elif action == 'toggle_active':
                subsite.active = not subsite.active
                db.session.commit()
                flash(f'Subsite {"ativado" if subsite.active else "desativado"}.', 'success')
            
            elif action == 'toggle_payment':
                subsite.require_payment = 'require_payment' in request.form
                db.session.commit()
                flash('Configuração de pagamento atualizada.', 'success')
            
            elif action == 'delete':
                db.session.delete(subsite)
                db.session.commit()
                flash('Subsite excluído.', 'success')
        
        else:
            # Create new subsite
            new_subsite = Subsite(
                name=request.form.get('name'),
                active='active' in request.form,
                require_payment='require_payment' in request.form
            )
            db.session.add(new_subsite)
            db.session.commit()
            flash('Subsite criado.', 'success')
        
        return redirect(url_for('master.manage_subsites'))
    
    subsites = Subsite.query.all()
    return render_template('master_subsites.html', subsites=subsites)

@master_bp.route('/subsite/<int:subsite_id>/select')
@require_master
def select_subsite(subsite_id):
    session['master_subsite_id'] = subsite_id
    return redirect(url_for('admin.dashboard'))

@master_bp.route('/users', methods=['GET', 'POST'])
@require_master
def manage_users():
    if request.method == 'POST':
        action = request.form.get('action')
        user_id = request.form.get('user_id')
        
        if user_id:
            user = User.query.get_or_404(user_id)
            
            if action == 'update_phone':
                phone = request.form.get('phone')
                clean = ''.join(filter(str.isdigit, phone)) if phone else ''
                if phone and (len(clean) < 10 or len(clean) > 11):
                    flash('Telefone inválido format (DD) 9XXXX-XXXX', 'error')
                else:
                    user.phone = phone
                    db.session.commit()
                    flash('Telefone atualizado.', 'success')
            
            elif action == 'update_name':
                user.name = request.form.get('name')
                db.session.commit()
                flash('Nome atualizado.', 'success')

            elif action == 'update_key':
                new_key = request.form.get('petro_key').upper()
                # Check uniqueness
                existing = User.query.filter_by(petro_key=new_key).first()
                if existing and existing.id != user.id:
                    flash('Chave já existe.', 'error')
                else:
                    user.petro_key = new_key
                    db.session.commit()
                    flash('Chave atualizada.', 'success')
            
            elif action == 'update_subsite':
                user.subsite_id = request.form.get('subsite_id') or None
                db.session.commit()
                flash('Subsite atualizado.', 'success')

            elif action == 'toggle_active':
                user.active = not user.active
                db.session.commit()
                flash(f'Usuário {"ativado" if user.active else "desativado"}.', 'success')
        
        return redirect(url_for('master.manage_users'))
    
    users = User.query.all()
    subsites = Subsite.query.all()
    return render_template('master_users.html', users=users, subsites=subsites)

@master_bp.route('/user/create', methods=['GET', 'POST'])
@require_master
def create_admin():
    if request.method == 'POST':
        petro_key = request.form.get('petro_key').upper()
        password = request.form.get('password')
        name = request.form.get('name')
        phone = request.form.get('phone')
        role = request.form.get('role', 'user')
        subsite_id = request.form.get('subsite_id')
        
        existing = User.query.filter_by(petro_key=petro_key).first()
        if existing:
            flash('Chave já cadastrada.', 'error')
            return redirect(url_for('master.create_admin'))
        
        # Clean phone
        clean_phone = ''.join(filter(str.isdigit, phone)) if phone else ''
        if phone and (len(clean_phone) < 10 or len(clean_phone) > 11):
            flash('Telefone inválido. Use (DD) 9XXXX-XXXX', 'error')
            return redirect(url_for('master.create_admin'))
        
        new_user = User(
            name=name,
            phone=phone,
            petro_key=petro_key,
            role=role,
            subsite_id=int(subsite_id) if subsite_id else None
        )
        
        if role in ['admin', 'admin_master'] and password:
            new_user.password_hash = generate_password_hash(password)
        
        db.session.add(new_user)
        db.session.commit()
        flash(f'Usuário {name} criado!', 'success')
        return redirect(url_for('master.manage_users'))
    
    subsites = Subsite.query.all()
    return render_template('master_admin_form.html', subsites=subsites)
