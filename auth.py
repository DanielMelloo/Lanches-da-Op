from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required
from werkzeug.security import check_password_hash
from models import User
from database import db

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login/<int:subsite_id>', methods=['GET'])
def login_subsite(subsite_id):
    from flask import session
    from models import Subsite
    
    sub = Subsite.query.get_or_404(subsite_id)
    session['target_subsite_id'] = subsite_id
    session['target_subsite_name'] = sub.name
    return redirect(url_for('auth.login'))

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    from flask import session
    target_subsite_name = session.get('target_subsite_name')
    
    if request.method == 'POST':
        petro_key = request.form.get('petro_key').upper()
        # No password needed for customers
        
        user = User.query.filter_by(petro_key=petro_key).first()
        
        if user:
            # Check if user is active
            if not user.active:
                flash('Usuário desativado.', 'error')
                return render_template('login.html', target_subsite=target_subsite_name)

            # Restrict: Only ROLE='user' can login here
            if user.role != 'user':
                flash('Administradores devem usar o Login Administrativo.', 'error')
                return render_template('login.html', target_subsite=target_subsite_name)
            
            # Login successful (Key only)
            login_user(user, remember=True)
            return redirect(url_for('index'))
        else:
            flash('Chave não encontrada', 'error')
            
    return render_template('login.html', target_subsite=target_subsite_name)

@auth_bp.route('/login/admin', methods=['GET', 'POST'])
def login_admin():
    if request.method == 'POST':
        petro_key = request.form.get('petro_key', '').upper()
        password = request.form.get('password')
        
        # Allow both admin and admin_master here
        user = User.query.filter(User.petro_key == petro_key, User.role.in_(['admin', 'admin_master'])).first()
        
        if user and user.password_hash and check_password_hash(user.password_hash, password):
            remember = 'remember' in request.form
            login_user(user, remember=remember)
            
            from flask import session
            session.permanent = True
            
            if user.role == 'admin_master':
                 flash(f'Bem-vindo, Master {user.name}!', 'success')
                 return redirect(url_for('master.dashboard'))
            else:
                 flash(f'Bem-vindo, {user.name}!', 'success')
                 return redirect(url_for('admin.dashboard'))
        else:
            flash('Credenciais administrativas inválidas.', 'error')
    
    # We can reuse login_master.html or create a generic login_admin.html
    # For now, let's render 'login_admin.html' (to be created)
    return render_template('login_admin.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    from flask import session
    target_subsite_id = session.get('target_subsite_id')
    target_subsite_name = session.get('target_subsite_name')
    
    # If generic register access but no subsite selected, maybe redirect or generic? 
    # For now, let's assume registration implies linking to the chosen subsite.
    
    if request.method == 'POST':
        petro_key = request.form.get('petro_key').upper()
        if not petro_key.isalnum() or len(petro_key) != 4:
            flash('Chave deve ter 4 caracteres alfanuméricos', 'error')
            return redirect(url_for('auth.register'))
            
        name = request.form.get('name')
        phone = request.form.get('phone')
        
        existing = User.query.filter_by(petro_key=petro_key).first()
        if existing:
            flash('Chave já cadastrada', 'error')
            return redirect(url_for('auth.login'))
            
        # Clean phone
        clean_phone = ''.join(filter(str.isdigit, phone)) if phone else ''
        if not phone or len(clean_phone) < 10 or len(clean_phone) > 11:
            flash('Telefone inválido. Use (DD) 9XXXX-XXXX', 'error')
            return redirect(url_for('auth.register'))
            
        new_user = User(
            name=name, 
            phone=phone, # Save with formatting or clean? Usually raw. But UI has mask. Let's save as input for now but valid.
            # Ideally save clean, but let's keep consistent with existing data which seems mixed or formatted.
            # User profile shows {{ current_user.phone or '' }}, mask handles formatting on input. 
            # Storing formatted is fine for small apps, strictly digits is better.
            # Let's simple check.
            petro_key=petro_key, 
            role='user',
            subsite_id=target_subsite_id # Link to selected subsite
        )
        db.session.add(new_user)
        db.session.commit()
        
        login_user(new_user)
        return redirect(url_for('index'))
        
    return render_template('register.html', target_subsite=target_subsite_name)

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login')) # Redirect to login instead of index for clarity

# Deprecate or alias login_master to login_admin if needed, but keeping for compatibility if linked elsewhere
@auth_bp.route('/login_master', methods=['GET', 'POST'])
def login_master():
    return redirect(url_for('auth.login_admin'))
