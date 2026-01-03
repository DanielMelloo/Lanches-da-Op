import os
from sqlalchemy import create_engine, text

# Tunnel Config
DB_USER = 'root'
DB_PASS = 'CodeEz4ever'
DB_HOST = '127.0.0.1'
DB_PORT = '3307'
DB_NAME = 'lanches_da_op'

DATABASE_URI = f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

def check():
    engine = create_engine(DATABASE_URI)
    print(f"--- Checking Stores Status (via Tunnel {DB_PORT}) ---")
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT id, name, pending_manual_dispatch FROM stores"))
            print(f"{'ID':<5} | {'Name':<30} | {'Pending Dispatch?'}")
            print("-" * 55)
            for row in result:
                # row is (id, name, pending)
                status = "YES (True)" if row[2] else "NO (False)"
                print(f"{row[0]:<5} | {row[1]:<30} | {status}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check()
