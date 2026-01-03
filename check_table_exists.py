from app import create_app
from database import db
import sqlalchemy

app = create_app()

with app.app_context():
    try:
        inspector = sqlalchemy.inspect(db.engine)
        tables = inspector.get_table_names()
        print(f"Current tables: {tables}")
        
        if 'whatsapp_template_presets' in tables:
            print("SUCCESS: Table 'whatsapp_template_presets' exists.")
        else:
            print("FAILURE: Table 'whatsapp_template_presets' DOES NOT EXIST.")
    except Exception as e:
        print(f"Error inspecting DB: {e}")
