import os
from sqlalchemy import create_engine, text

# Tunnel config
uri = 'mysql+pymysql://root:CodeEz4ever@127.0.0.1:3307/lanches_da_op'

def migrate():
    engine = create_engine(uri)
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE sectors ADD COLUMN type VARCHAR(20) DEFAULT 'location'"))
            conn.commit()
            print("Migration successful: Added 'type' column.")
            
            # Optional: Clean up known scraper categories from being 'location'
            # Assuming scraper categories are unique names like 'Espetos', 'Acompanhamentos'
            # We can update them to 'category'
            
            conn.execute(text("UPDATE sectors SET type='category' WHERE name IN ('Espetos', 'Acompanhamentos', 'Os mais pedidos', 'Bebidas', 'Doces', 'Jantinha')"))
            conn.commit()
            print("Migration: Updated known categories to type='category'")
            
        except Exception as e:
            if "Duplicate column" in str(e):
                print("Column already exists.")
            else:
                print(f"Migration failed: {e}")

if __name__ == "__main__":
    migrate()
