import os
from sqlalchemy import create_engine, text

# Tunnel config
uri = 'mysql+pymysql://root:CodeEz4ever@127.0.0.1:3307/lanches_da_op'

def migrate():
    engine = create_engine(uri)
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE items ADD COLUMN description TEXT"))
            conn.commit()
            print("Migration successful: Added 'description' column.")
        except Exception as e:
            if "Duplicate column" in str(e):
                print("Column already exists.")
            else:
                print(f"Migration failed: {e}")

if __name__ == "__main__":
    migrate()
