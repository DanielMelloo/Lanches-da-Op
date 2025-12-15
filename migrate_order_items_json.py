import os
# Override DB config
os.environ['DB_HOST'] = '127.0.0.1:3307'
os.environ['DB_USER'] = 'root'
os.environ['DB_PASSWORD'] = 'CodeEz4ever'
os.environ['DB_NAME'] = 'lanches_da_op'
os.environ['SKIP_SCHEDULER'] = 'true'

from app import create_app, db
from sqlalchemy import text

def migrate():
    app = create_app()
    with app.app_context():
        # Check if column exists
        with db.engine.connect() as conn:
            result = conn.execute(text("SHOW COLUMNS FROM order_items LIKE 'subitems_json'"))
            if result.fetchone():
                print("Column 'subitems_json' already exists in 'order_items'.")
            else:
                print("Adding column 'subitems_json' to 'order_items'...")
                conn.execute(text("ALTER TABLE order_items ADD COLUMN subitems_json JSON"))
                conn.commit()
                print("Migration successful.")

if __name__ == "__main__":
    migrate()
