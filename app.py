import os
# Fix for ZoneInfoNotFoundError in some environments (like AL2023)
# Set TZ before imports that use it (like APScheduler)
os.environ['TZ'] = 'America/Sao_Paulo'

from flask import Flask, render_template, g, session, redirect, url_for
from flask_login import LoginManager, current_user
from dotenv import load_dotenv
import os
from database import db, init_db
from models import User

load_dotenv()

login_manager = LoginManager()
login_manager.login_view = 'auth.login'

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev')
    
    # Construct DB URI from individual variables to ensure consistency with user comment
    db_user = os.getenv('DB_USER', 'root')
    db_pass = os.getenv('DB_PASSWORD', '')
    db_host = os.getenv('DB_HOST', 'localhost')
    db_name = os.getenv('DB_NAME', 'lanches_db')
    
    # Handle empty password case
    if db_pass:
        app.config['SQLALCHEMY_DATABASE_URI'] = f"mysql+pymysql://{db_user}:{db_pass}@{db_host}/{db_name}"
    else:
        app.config['SQLALCHEMY_DATABASE_URI'] = f"mysql+pymysql://{db_user}@{db_host}/{db_name}"
        
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Persistent Sessions (Remember Me)
    from datetime import timedelta
    app.config['REMEMBER_COOKIE_DURATION'] = timedelta(days=30)
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)

    init_db(app)
    login_manager.init_app(app)

    # Register Blueprints
    from auth import auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')
    
    from routes_user import user_bp
    app.register_blueprint(user_bp)

    from routes_master import master_bp
    app.register_blueprint(master_bp)

    from routes_admin import admin_bp
    app.register_blueprint(admin_bp)

    from routes_webhook import webhook_bp
    app.register_blueprint(webhook_bp)

    # -----------------------------------------------------------
    # Background Scheduler for Payment Verification
    # -----------------------------------------------------------
    # -----------------------------------------------------------
    # Background Scheduler for Payment Verification
    # -----------------------------------------------------------
    from extensions import scheduler
    
    # Import the task function
    from services.tasks import check_all_pending_payments
    
    # Schedule default (30s) if not already scheduled
    if not scheduler.get_job('check_payments'):
        scheduler.add_job(id='check_payments', func=check_all_pending_payments, trigger='interval', seconds=30)
        
    
    scheduler.init_app(app)
    
    # Avoid starting scheduler twice when using reloader on Windows (fixes WinError 10038)
    # Also skip if SKIP_SCHEDULER is set (for local workers)
    if (not app.debug or os.environ.get('WERKZEUG_RUN_MAIN') == 'true') and not os.environ.get('SKIP_SCHEDULER'):
        if not scheduler.running:
            scheduler.start()
    # -----------------------------------------------------------

    @app.route('/fix_schema_orders')
    def fix_schema_orders():
        with app.app_context():
            # Add pix_code_copy_paste to orders
            try:
                with db.engine.connect() as conn:
                    conn.execute(db.text("ALTER TABLE orders ADD COLUMN pix_code_copy_paste TEXT;"))
                return "Old schema updated: Added pix_code_copy_paste to orders."
            except Exception as e:
                return f"Error updating schema: {e}"

    @app.route('/fix_schema_efi')
    def fix_schema_efi():
        with app.app_context():
            try:
                with db.engine.connect() as conn:
                    # Add columns if not exist
                    cols = [
                        "efi_active BOOLEAN DEFAULT 1",
                        "efi_mode VARCHAR(20) DEFAULT 'producao'",
                        "efi_client_id VARCHAR(255)",
                        "efi_client_secret VARCHAR(255)",
                        "efi_pix_key VARCHAR(255)",
                        "efi_cert_name VARCHAR(255)",
                        "payment_check_interval INT DEFAULT 30",
                        "enable_auto_check BOOLEAN DEFAULT 1"
                    ]
                    for col in cols:
                        try:
                            conn.execute(db.text(f"ALTER TABLE subsites ADD COLUMN {col};"))
                        except Exception as e:
                            print(f"Col exists or error: {e}")
                            
                # Migration: Copy from ENV to DB for first subsite found
                from models import Subsite
                subsite = Subsite.query.first()
                if subsite:
                    import os
                    subsite.efi_client_id = os.getenv('EFI_CLIENT_ID')
                    subsite.efi_client_secret = os.getenv('EFI_CLIENT_SECRET')
                    subsite.efi_pix_key = os.getenv('EFI_PIX_KEY')
                    subsite.efi_mode = os.getenv('EFI_MODE', 'producao')
                    # Cert logic: pick based on mode
                    if subsite.efi_mode == 'producao':
                         cert = os.getenv('EFI_CERT_PEM_PRODUCAO')
                    else:
                         cert = os.getenv('EFI_CERT_PEM_HOMOLOGACAO')
                    if cert and '/' in cert: 
                         subsite.efi_cert_name = cert.split('/')[-1] # take filename
                    elif cert:
                         subsite.efi_cert_name = cert
                    
                    db.session.commit()
                    return f"Schema updated and ENV migrated to Subsite {subsite.name}"
                return "Schema updated but no subsite found to migrate ENV."
                
            except Exception as e:
                return f"Error updating schema: {e}"

    @app.route('/')
    def index():
        if current_user.is_authenticated:
            return redirect(url_for('user.dashboard'))
        
        # Public Landing Page with Subsites
        from models import Subsite
        subsites = Subsite.query.filter_by(active=True).all()
        return render_template('landing.html', subsites=subsites)

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(
        debug=True,
        port=8000,
        host="0.0.0.0"
    )
