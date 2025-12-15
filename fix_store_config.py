import os
import json
from sqlalchemy import create_engine, text

# Tunnel config
uri = 'mysql+pymysql://root:CodeEz4ever@127.0.0.1:3307/lanches_da_op'

def fix():
    engine = create_engine(uri)
    config = {
        "url": "https://app.anota.ai/m/JLS7eh7xw",
        "active": True,
        "mode": "update"
    }
    json_str = json.dumps(config)
    
    with engine.connect() as conn:
        try:
            # Use JSON_SET or just overwrite if it's text
            # MariaDB JSON column is just a check constraint usually, but let's pass a string
            conn.execute(
                text("UPDATE stores SET scraper_config = :cfg, scraper_status = 'pending' WHERE id=1"),
                {"cfg": json_str}
            )
            conn.commit()
            print("Config updated successfully.")
        except Exception as e:
            print(f"Update failed: {e}")

if __name__ == "__main__":
    fix()
