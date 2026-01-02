from app import create_app
from database import db
from sqlalchemy import text

app = create_app()
with app.app_context():
    try:
        db.session.execute(text("ALTER TABLE subsites ADD COLUMN order_opening_time VARCHAR(5) DEFAULT '08:00' AFTER efi_cert_name"))
        db.session.commit()
        print("Migration successful: added order_opening_time")
    except Exception as e:
        db.session.rollback()
        print(f"Migration failed or already applied: {e}")
