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
    
    # Background Scheduler Settings
    payment_check_interval = db.Column(db.Integer, default=30)
    enable_auto_check = db.Column(db.Boolean, default=True)
    
    # Relationships
    users = db.relationship('User', backref='subsite', lazy=True)
    stores = db.relationship('Store', backref='subsite', lazy=True)
    sectors = db.relationship('Sector', backref='subsite', lazy=True)
    orders = db.relationship('Order', backref='subsite', lazy=True)

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
    
    subsite_id = db.Column(db.Integer, db.ForeignKey('subsites.id'), nullable=False)

class Item(db.Model):
    __tablename__ = 'items'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    active = db.Column(db.Boolean, default=True)
    image_url = db.Column(db.String(500))
    subitems_json = db.Column(db.JSON)  # Structure: [{"title": "Principal", "type": "radio", "options": ["frango", "bife"]}, ...]
    store_id = db.Column(db.Integer, db.ForeignKey('stores.id'), nullable=False)
    store = db.relationship('Store', backref='items')

class Sector(db.Model):
    __tablename__ = 'sectors'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
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
