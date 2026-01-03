import pymysql
from app import create_app
import re

app = create_app()

def fix_all_db():
    uri = app.config['SQLALCHEMY_DATABASE_URI']
    # Extract credentials
    match = re.search(r'mysql\+pymysql://([^:]+):([^@]+)@([^/]+)/(.+)', uri)
    if not match:
        print("Invalid URI format")
        return

    user, password, host, db_name = match.groups()
    
    # Force Tunnel Connection for Production Fix
    host = '127.0.0.1'
    port = 3307
    
    # Force correct DB name based on previous experience (fix_db.py)
    # The URI often has 'lanches_da_op' but the real DB is 'lanches_db'
    target_db = 'lanches_da_op' 
    
    print(f"Connecting to {host}:{port} as {user} to update {target_db}...")
    
    try:
        conn = pymysql.connect(
            host=host,
            user=user,
            password=password,
            database=target_db,
            port=port,
            cursorclass=pymysql.cursors.DictCursor
        )
        
        with conn.cursor() as cursor:
            # 1. Create whatsapp_template_presets TABLE
            print("Checking table 'whatsapp_template_presets'...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS whatsapp_template_presets (
                    id INTEGER NOT NULL AUTO_INCREMENT,
                    name VARCHAR(100) NOT NULL,
                    content TEXT,
                    subsite_id INTEGER,
                    PRIMARY KEY (id),
                    FOREIGN KEY(subsite_id) REFERENCES subsites(id)
                )
            """)
            print("- Table verified/created.")

            # 2. Check/Add Columns to 'stores'
            print("Checking 'stores' columns...")
            
            # Helper to add column safely
            def ensure_column(col_name, col_def):
                cursor.execute(f"SHOW COLUMNS FROM stores LIKE '{col_name}'")
                if cursor.fetchone():
                    print(f"- Column '{col_name}' exists.")
                else:
                    print(f"- Adding column '{col_name}'...")
                    cursor.execute(f"ALTER TABLE stores ADD COLUMN {col_name} {col_def}")
                    print(f"- Column '{col_name}' added.")

            ensure_column('auto_send_on_close', 'BOOLEAN DEFAULT TRUE')
            ensure_column('pending_manual_dispatch', 'BOOLEAN DEFAULT FALSE')
            ensure_column('whatsapp_template', 'TEXT')

            # 3. Check 'auto_send_whatsapp' on subsites
            print("Checking 'subsites' columns...")
            cursor.execute("SHOW COLUMNS FROM subsites LIKE 'auto_send_whatsapp'")
            if not cursor.fetchone():
                print("- Adding 'auto_send_whatsapp' to subsites...")
                cursor.execute("ALTER TABLE subsites ADD COLUMN auto_send_whatsapp BOOLEAN DEFAULT TRUE")
                cursor.execute("UPDATE subsites SET auto_send_whatsapp = TRUE")

            conn.commit()
            print("\nSUCCESS: Database verification and update complete.")
                
        conn.close()
    except Exception as e:
        print(f"\nCRITICAL ERROR: {e}")

if __name__ == "__main__":
    fix_all_db()
