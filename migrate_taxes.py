from app import app, db
from sqlalchemy import text

def migrate():
    with app.app_context():
        # Check columns using raw SQL or inspection. 
        # Simplest way for SQLite/MySQL is to try adding them and catch errors, or inspect.
        # Assuming MySQL per 'pymysql' dependency, or SQLite? User Env says windows, run_loop...
        # Let's assume generic SQL that fits SQLite (no IF NOT EXISTS in ALTER COLUMN typically).
        # But dependency 'pymysql' suggests MySQL. 
        # Check connection uri?
        
        conn = db.engine.connect()
        try:
            # We will try to add columns one by one. If they exist, it might fail, we catch it.
            # MySQL syntax: ALTER TABLE subsite ADD COLUMN ...
            # SQLite syntax: ALTER TABLE subsite ADD COLUMN ...
            
            columns = [
                ("tax_mode", "VARCHAR(20) DEFAULT 'fixed'"),
                ("fixed_tax_value", "FLOAT DEFAULT 0.0"),
                ("variable_tax_settings", "JSON"),
                ("calculated_variable_tax", "FLOAT DEFAULT 0.0"),
                ("enable_site_payment", "BOOLEAN DEFAULT 0") # SQLite uses 0/1, MySQL uses BOOLEAN/TINYINT
            ]
            
            for col_name, col_def in columns:
                try:
                    query = text(f"ALTER TABLE subsite ADD COLUMN {col_name} {col_def}")
                    conn.execute(query)
                    print(f"Added column {col_name}")
                except Exception as e:
                    print(f"Column {col_name} might already exist or error: {e}")
                    
            conn.commit()
            print("Migration attempt finished.")
        finally:
            conn.close()

if __name__ == "__main__":
    migrate()
