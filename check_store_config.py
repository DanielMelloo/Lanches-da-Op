import os
from sqlalchemy import create_engine, text

# Tunnel config
uri = 'mysql+pymysql://root:CodeEz4ever@127.0.0.1:3307/lanches_da_op'

def check():
    engine = create_engine(uri)
    with engine.connect() as conn:
        res = conn.execute(text("SELECT id, name, scraper_config, scraper_status FROM stores WHERE id=1"))
        row = res.fetchone()
        if row:
            print(f"ID: {row[0]}")
            print(f"Name: {row[1]}")
            print(f"Scraper Config: {row[2]}")
            print(f"Scraper Status: {row[3]}")
        else:
            print("Store 1 not found")

if __name__ == "__main__":
    check()
