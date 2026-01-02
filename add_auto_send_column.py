import pymysql
from app import create_app
import re

app = create_app()

def run_migration():
    uri = app.config['SQLALCHEMY_DATABASE_URI']
    # Extract credentials
    match = re.search(r'mysql\+pymysql://([^:]+):([^@]+)@([^/]+)/(.+)', uri)
    if not match:
        print("Invalid URI format")
        return

    user, password, host, db_name = match.groups()
    
    # Force correct DB name (URI has lanches_da_op which is wrong/alias)
    db_name = 'lanches_db' 

    print(f"Connecting to {host} as {user} to update {db_name}...")
    
    try:
        conn = pymysql.connect(
            host=host,
            user=user,
            password=password,
            database=db_name, # Explicit DB
            cursorclass=pymysql.cursors.DictCursor
        )
        
        with conn.cursor() as cursor:
            # Check if column exists
            cursor.execute("SHOW COLUMNS FROM stores LIKE 'auto_send_on_close'")
            if cursor.fetchone():
                print("Column 'auto_send_on_close' already exists.")
            else:
                print("Adding 'auto_send_on_close' column...")
                cursor.execute("ALTER TABLE stores ADD COLUMN auto_send_on_close BOOLEAN DEFAULT TRUE")
                conn.commit()
                print("SUCCESS: Column added.")
                
        conn.close()
    except Exception as e:
        print(f"Migration FAILED: {e}")

if __name__ == "__main__":
    run_migration()
