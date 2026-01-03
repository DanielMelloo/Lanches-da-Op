import sys
import traceback

print("Attempting to import app...")
try:
    from app import create_app
    print("Import successful. Creating app...")
    app = create_app()
    print("App created successfully!")
    
    with app.app_context():
        from models import WhatsappTemplatePreset
        print("Model WhatsappTemplatePreset imported successfully.")
        
except Exception:
    print("FATAL ERROR DURING STARTUP:")
    traceback.print_exc()
