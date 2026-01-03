from app import create_app
from database import db
from sqlalchemy import inspect

app = create_app()

with app.app_context():
    try:
        print("URI:", app.config['SQLALCHEMY_DATABASE_URI'])
        inspector = inspect(db.engine)
        exists = 'whatsapp_template_presets' in inspector.get_table_names()
        print(f"VERIFICATION_RESULT: {exists}")
    except Exception as e:
        print(f"FULL ERROR: {e}")
        import traceback
        traceback.print_exc()
