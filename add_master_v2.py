from app import create_app, db
from models import User
from werkzeug.security import generate_password_hash

def add_master():
    app = create_app()
    with app.app_context():
        # Master User Data
        name = "Daniel"
        key = "FWAP"
        raw_pass = "CodeEz4ever"
        
        existing = User.query.filter_by(petro_key=key).first()
        
        if existing:
            print(f"User {name} (Key {key}) found. Updating to Master Admin...")
            existing.name = name
            existing.password_hash = generate_password_hash(raw_pass)
            existing.role = 'admin_master'
            existing.active = True
        else:
            print(f"Creating new Master Admin {name}...")
            new_user = User(
                name=name,
                petro_key=key,
                password_hash=generate_password_hash(raw_pass),
                role='admin_master',
                active=True
            )
            db.session.add(new_user)
            
        db.session.commit()
        print("Master User configured successfully!")

if __name__ == "__main__":
    add_master()
