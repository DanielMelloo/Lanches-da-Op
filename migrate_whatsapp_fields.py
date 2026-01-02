from app import create_app
from database import db
from sqlalchemy import text

app = create_app()
with app.app_context():
    try:
        # Add whatsapp_number to stores
        try:
            db.session.execute(text("ALTER TABLE stores ADD COLUMN whatsapp_number VARCHAR(20) AFTER scraper_last_run"))
            print("Successfully added whatsapp_number to stores")
        except Exception as e:
            print(f"whatsapp_number already exists or error: {e}")
            
        # Add whatsapp_dispatched to orders
        try:
            db.session.execute(text("ALTER TABLE orders ADD COLUMN whatsapp_dispatched BOOLEAN DEFAULT FALSE AFTER pix_code_copy_paste"))
            print("Successfully added whatsapp_dispatched to orders")
        except Exception as e:
            print(f"whatsapp_dispatched already exists or error: {e}")
            
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Global migration error: {e}")
