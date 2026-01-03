from app import create_app
from database import db
from sqlalchemy import text

app = create_app()

sql = """
CREATE TABLE IF NOT EXISTS whatsapp_template_presets (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    content TEXT NOT NULL,
    subsite_id INT NOT NULL,
    FOREIGN KEY (subsite_id) REFERENCES subsites(id)
);
"""

with app.app_context():
    try:
        print("Executing Raw SQL to create table...")
        with db.engine.connect() as connection:
            connection.execute(text(sql))
            # connection.commit() # Not always needed depending on isolation, but safe for DDL
        print("SQL Executed successfully.")
    except Exception as e:
        print(f"FAILED: {e}")
        import traceback
        traceback.print_exc()
