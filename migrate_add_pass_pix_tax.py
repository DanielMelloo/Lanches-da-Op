from app import create_app, db
from sqlalchemy import text

def migrate():
    app = create_app()
    with app.app_context():
        conn = db.engine.connect()
        try:
            # Add pass_pix_tax column
            try:
                query = text("ALTER TABLE subsites ADD COLUMN pass_pix_tax BOOLEAN DEFAULT 0")
                conn.execute(query)
                print("Added column pass_pix_tax")
            except Exception as e:
                print(f"Column pass_pix_tax might already exist or error: {e}")
                
            conn.commit()
            print("Migration attempt finished.")
        finally:
            conn.close()

if __name__ == "__main__":
    migrate()
