from database import db
from datetime import datetime
import pytz
from flask_login import UserMixin

def get_sp_time():
    return datetime.now(pytz.timezone('America/Sao_Paulo'))

class Subsite(db.Model):
    __tablename__ = 'subsites'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    active = db.Column(db.Boolean, default=True)
    require_payment = db.Column(db.Boolean, default=False)
    pass_pix_tax = db.Column(db.Boolean, default=False)
    
    # Advanced Tax Fields
    tax_mode = db.Column(db.String(20), default='fixed') # 'fixed' or 'variable'
    fixed_tax_value = db.Column(db.Float, default=0.0)
    variable_tax_settings = db.Column(db.JSON)
    calculated_variable_tax = db.Column(db.Float, default=0.0)
    
    # EFí Configuration
    efi_active = db.Column(db.Boolean, default=True) # Global toggle for EFí integration on this subsite
    efi_mode = db.Column(db.String(20), default='producao') # 'homologacao' or 'producao'
    efi_client_id = db.Column(db.String(255))
    efi_client_secret = db.Column(db.String(255))
    efi_pix_key = db.Column(db.String(255))
    efi_cert_name = db.Column(db.String(255)) # filename in certs/
    
    # Order Closing Schedule
    order_opening_time = db.Column(db.String(5), default='08:00') # HH:MM
    order_closing_time = db.Column(db.String(5), default='23:59') # HH:MM
    closing_time_active = db.Column(db.Boolean, default=False)
    temp_open_until = db.Column(db.DateTime) # Temporal extension
    
    # Relationships
    users = db.relationship('User', backref='subsite', lazy=True)
    stores = db.relationship('Store', backref='subsite', lazy=True)
    sectors = db.relationship('Sector', backref='subsite', lazy=True)
    orders = db.relationship('Order', backref='subsite', lazy=True)

    def is_open(self):
        """Checks if the subsite is currently accepting orders."""
        if not self.active:
            return False
            
        now = get_sp_time()
        
        # 1. Temporary extension override
        if self.temp_open_until:
            target = self.temp_open_until
            if target.tzinfo is None:
                target = pytz.timezone('America/Sao_Paulo').localize(target)
            
            if now < target:
                return True
                
        # 2. Daily window check
        if self.closing_time_active and self.order_opening_time and self.order_closing_time:
            try:
                # Convert strings to minutes for easier comparison
                def to_minutes(t_str):
                    h, m = map(int, t_str.split(':'))
                    return h * 60 + m
                
                now_min = now.hour * 60 + now.minute
                open_min = to_minutes(self.order_opening_time)
                close_min = to_minutes(self.order_closing_time)
                
                if open_min == close_min:
                    # If times are equal, it's effectively closed for automated window
                    # unless they intend 24h, but usually they'd toggle 'Auto' off for that.
                    print(f"DEBUG: Subsite {self.name} closed (Equal Times). Open: {open_min}, Close: {close_min}")
                    return False
                    
                if open_min < close_min:
                    # Normal shift (e.g. 08:00 to 22:00)
                    if not (open_min <= now_min < close_min):
                        print(f"DEBUG: Subsite {self.name} closed (Normal Shift). Now: {now_min}, Open: {open_min}, Close: {close_min}")
                        return False
                else:
                    # Overnight shift (e.g. 18:00 to 02:00)
                    # Open if: now >= 18:00 OR now < 02:00
                    if not (now_min >= open_min or now_min < close_min):
                        print(f"DEBUG: Subsite {self.name} closed (Overnight). Now: {now_min}, Open: {open_min}, Close: {close_min}")
                        return False
            except Exception as e:
                print(f"Error checking schedule: {e}")
                pass # Fallback to open if misconfigured
                
        return True

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20))
    petro_key = db.Column(db.String(4), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    role = db.Column(db.Enum('user', 'admin', 'admin_master'), default='user')
    subsite_id = db.Column(db.Integer, db.ForeignKey('subsites.id'))
    created_at = db.Column(db.DateTime, default=get_sp_time)
    active = db.Column(db.Boolean, default=True)

    @property
    def is_active(self):
        return self.active

    def get_id(self):
        return str(self.id)

class Store(db.Model):
    __tablename__ = 'stores'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    active = db.Column(db.Boolean, default=True)
    
    # Scraper
    scraper_config = db.Column(db.JSON)
    scraper_status = db.Column(db.String(20), default='idle')
    scraper_last_run = db.Column(db.DateTime)
    whatsapp_number = db.Column(db.String(20))
    whatsapp_template = db.Column(db.Text) # Custom message template
    pending_manual_dispatch = db.Column(db.Boolean, default=False)
    
    subsite_id = db.Column(db.Integer, db.ForeignKey('subsites.id'), nullable=False)

class Item(db.Model):
    __tablename__ = 'items'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Float, nullable=False)
    active = db.Column(db.Boolean, default=True)
    image_url = db.Column(db.String(500))
    subitems_json = db.Column(db.JSON)  # Structure: [{"title": "Principal", "type": "radio", "options": ["frango", "bife"]}, ...]
    store_id = db.Column(db.Integer, db.ForeignKey('stores.id'), nullable=False)
    sector_id = db.Column(db.Integer, db.ForeignKey('sectors.id'))
    store = db.relationship('Store', backref='items')
    sector = db.relationship('Sector', backref='items')

class Sector(db.Model):
    __tablename__ = 'sectors'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    type = db.Column(db.String(20), default='location') # 'location' (tables) or 'category' (menu)
    active = db.Column(db.Boolean, default=True)
    subsite_id = db.Column(db.Integer, db.ForeignKey('subsites.id'))

class Status(db.Model):
    __tablename__ = 'statuses'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    type = db.Column(db.String(20))
    sort_order = db.Column(db.Integer, default=0)
    subsite_id = db.Column(db.Integer)

class Order(db.Model):
    __tablename__ = 'orders'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    subsite_id = db.Column(db.Integer, db.ForeignKey('subsites.id'), nullable=False)
    sector_id = db.Column(db.Integer, db.ForeignKey('sectors.id'))
    status_id = db.Column(db.Integer, db.ForeignKey('statuses.id'), nullable=False)
    section = db.Column(db.String(50))
    
    total_items = db.Column(db.Float, default=0.0)
    tax_fixed = db.Column(db.Float, default=0.0)
    service_fee = db.Column(db.Float, default=0.0)
    total_general = db.Column(db.Float, default=0.0)
    
    payment_required = db.Column(db.Boolean, default=False)
    payment_status = db.Column(db.String(20), default='pending')
    pix_charge_id = db.Column(db.String(100))
    pix_code_copy_paste = db.Column(db.Text)
    whatsapp_dispatched = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=get_sp_time)
    
    user = db.relationship('User', backref='orders')
    sector = db.relationship('Sector')
    status = db.relationship('Status')
    order_items = db.relationship('OrderItem', backref='order', lazy=True, cascade="all, delete-orphan")

class OrderItem(db.Model):
    __tablename__ = 'order_items'
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('items.id', ondelete='CASCADE'), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    price_at_moment = db.Column(db.Float, nullable=False)
    subtotal = db.Column(db.Float, nullable=False)
    subitems_json = db.Column(db.JSON)
    
    item = db.relationship('Item')
