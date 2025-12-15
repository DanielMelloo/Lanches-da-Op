from app import create_app, db
from sqlalchemy import text

def migrate():
    app = create_app()
    with app.app_context():
        with db.engine.connect() as conn:
            # Add scraper_status to stores
            try:
                query = text("ALTER TABLE stores ADD COLUMN scraper_status VARCHAR(20) DEFAULT 'idle'")
                conn.execute(query)
                print("Added column scraper_status to stores")
            except Exception as e:
                print(f"stores.scraper_status might already exist: {e}")

            # Add scraper_last_run to stores
            try:
                query = text("ALTER TABLE stores ADD COLUMN scraper_last_run DATETIME")
                conn.execute(query)
                print("Added column scraper_last_run to stores")
            except Exception as e:
                print(f"stores.scraper_last_run might already exist: {e}")

            conn.commit()
            print("Scraper status migration finished.")

if __name__ == "__main__":
    migrate()
