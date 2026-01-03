from app import create_app, db
from sqlalchemy import text

app = create_app()

def check_and_add_column(table, column, col_type):
    try:
        # Check if column exists
        result = db.session.execute(text(f"SHOW COLUMNS FROM {table} LIKE '{column}'")).fetchone()
        if not result:
            print(f"Adding column '{column}' to table '{table}'...")
            db.session.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}"))
            db.session.commit()
            print("Done.")
        else:
            print(f"Column '{column}' already exists in '{table}'.")
    except Exception as e:
        print(f"Error checking/adding column {column}: {e}")
        db.session.rollback()

def create_presets_table():
    try:
        # Simple check if table exists
        result = db.session.execute(text("SHOW TABLES LIKE 'whatsapp_template_presets'")).fetchone()
        if not result:
            print("Creating table 'whatsapp_template_presets'...")
            # We use the model definition from SQLAlchemy effectively via create_all for missing tables?
            # Or manual SQL. Manual is safer if we don't want to use db.create_all() which might be silent or complex.
            sql = """
            CREATE TABLE whatsapp_template_presets (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                content TEXT NOT NULL,
                subsite_id INT NOT NULL,
                FOREIGN KEY (subsite_id) REFERENCES subsites(id)
            )
            """
            db.session.execute(text(sql))
            db.session.commit()
            print("Table created.")
        else:
            print("Table 'whatsapp_template_presets' already exists.")
    except Exception as e:
        print(f"Error creating presets table: {e}")

if __name__ == "__main__":
    with app.app_context():
        print("Starting Schema Update...")
        
        # Stores Columns
        check_and_add_column('stores', 'whatsapp_template', 'TEXT')
        check_and_add_column('stores', 'auto_send_on_close', 'TINYINT(1) DEFAULT 1')
        check_and_add_column('stores', 'pending_manual_dispatch', 'TINYINT(1) DEFAULT 0')
        
        # Presets Table
        create_presets_table()
        
        print("Schema Update Completed.")
