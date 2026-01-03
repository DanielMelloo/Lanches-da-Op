import os
from sqlalchemy import create_engine, text

DB_USER = 'root'
DB_PASS = 'CodeEz4ever'
DB_HOST = '127.0.0.1'
DB_PORT = '3307'
DB_NAME = 'lanches_da_op'

DATABASE_URI = f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

def reset():
    engine = create_engine(DATABASE_URI)
    print("--- Resetting Order 17 Status ---")
    try:
        with engine.connect() as conn:
            conn.execute(text("UPDATE orders SET whatsapp_dispatched = FALSE WHERE id = 17"))
            conn.commit()
            print("SUCCESS: Order 17 marked as PENDING (False).")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    reset()
