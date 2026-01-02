import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

def migrate():
    # Construct DB URI manually
    db_user = os.getenv('DB_USER', 'root')
    db_pass = os.getenv('DB_PASSWORD', '')
    db_host = os.getenv('DB_HOST', 'localhost')
    db_name = os.getenv('DB_NAME', 'lanches_db')
    
    if db_pass:
        uri = f"mysql+pymysql://{db_user}:{db_pass}@{db_host}/{db_name}"
    else:
        uri = f"mysql+pymysql://{db_user}@{db_host}/{db_name}"

    engine = create_engine(uri)
    
    with engine.connect() as conn:
        print("Checking for existing columns...")
        try:
            conn.execute(text("SELECT order_closing_time FROM subsites LIMIT 1"))
            print("Columns already exist.")
            return
        except Exception:
            pass

        print("Adding closing schedule columns to subsites table...")
        
        commands = [
            "ALTER TABLE subsites ADD COLUMN order_closing_time VARCHAR(5) DEFAULT '23:59'",
            "ALTER TABLE subsites ADD COLUMN closing_time_active BOOLEAN DEFAULT 0",
            "ALTER TABLE subsites ADD COLUMN temp_open_until DATETIME"
        ]
        
        for cmd in commands:
            try:
                conn.execute(text(cmd))
                print(f"Executed: {cmd}")
            except Exception as e:
                print(f"Col might already exist or error executing {cmd}: {e}")
        
        conn.commit()
        print("Migration completed.")

if __name__ == "__main__":
    migrate()
