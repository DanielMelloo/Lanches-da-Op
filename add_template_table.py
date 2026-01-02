from app import create_app
from database import db
# Ensure models are imported so they are registered in SQLAlchemy Metadata
from models import WhatsappTemplatePreset 

app = create_app()

with app.app_context():
    import sqlalchemy
    try:
        print("Checking for existing tables...")
        inspector = sqlalchemy.inspect(db.engine)
        tables = inspector.get_table_names()
        print(f"Existing tables: {tables}")
        
        if 'whatsapp_template_presets' in tables:
            print("Table 'whatsapp_template_presets' ALREADY EXISTS.")
        else:
            print("Table NOT found. Creating...")
            WhatsappTemplatePreset.__table__.create(db.engine)
            print("Table created successfully!")
            
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
