from flask_sqlalchemy import SQLAlchemy
from flask import Flask

db = SQLAlchemy()

def init_db(app: Flask):
    db.init_app(app)
    with app.app_context():
        # Ideally, we'd only create if they don't exist, but for now we assume schema.sql 
        # is the source of truth for schema creation if running the SQL script manually. 
        # However, for an ORM approach, we might want models.
        # For this MVP, we will try to reflect or use models.
        pass
