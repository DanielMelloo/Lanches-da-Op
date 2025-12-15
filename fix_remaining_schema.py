from app import create_app, db
from sqlalchemy import text

def migrate():
    app = create_app()
    with app.app_context():
        with db.engine.connect() as conn:
            # Fix stores.scraper_config
            try:
                query = text("ALTER TABLE stores ADD COLUMN scraper_config JSON")
                conn.execute(query)
                print("Added column scraper_config to stores")
            except Exception as e:
                print(f"stores.scraper_config error (likely exists): {e}")

            # Fix sectors.active
            try:
                query = text("ALTER TABLE sectors ADD COLUMN active BOOLEAN DEFAULT 1")
                conn.execute(query)
                print("Added column active to sectors")
            except Exception as e:
                print(f"sectors.active error (likely exists): {e}")
            
            conn.commit()
            print("Remaining migrations finished.")

if __name__ == "__main__":
    migrate()
