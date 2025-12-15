from app import create_app, db
from sqlalchemy import text

def migrate():
    app = create_app()
    with app.app_context():
        # Check if column exists, if not add it
        try:
            with db.engine.connect() as conn:
                try:
                    query = text("ALTER TABLE stores ADD COLUMN scraper_config JSON")
                    conn.execute(query)
                    conn.commit()
                    print("Added column scraper_config to stores")
                except Exception as e:
                    print(f"Column scraper_config might already exist or error: {e}")
        except Exception as e:
            print(f"Connection error: {e}")

if __name__ == "__main__":
    migrate()
