from app import create_app
from database import db
from models import User, Subsite
from werkzeug.security import generate_password_hash

app = create_app()

def add_daniel():
    with app.app_context():
        # Check for any subsite
        subsite = Subsite.query.first()
        if not subsite:
            print("No subsite found. Creating 'Unidade Padrao'...")
            subsite = Subsite(name='Unidade Padrao', active=True)
            db.session.add(subsite)
            db.session.commit()
            print(f"Created subsite: {subsite.name} (ID: {subsite.id})")
        else:
            print(f"Using existing subsite: {subsite.name} (ID: {subsite.id})")

        # Create or Update User
        petro_key = 'FWAP'
        existing = User.query.filter_by(petro_key=petro_key).first()
        
        if existing:
            print(f"User with key {petro_key} already exists. Updating...")
            existing.name = 'Daniel'
            existing.password_hash = generate_password_hash('CodeEz4ever')
            existing.role = 'admin'
            existing.subsite_id = subsite.id
            db.session.commit()
            print("User updated successfully.")
        else:
            new_user = User(
                name='Daniel',
                petro_key=petro_key,
                role='admin',
                subsite_id=subsite.id,
                phone='00000000',
                password_hash=generate_password_hash('CodeEz4ever')
            )
            db.session.add(new_user)
            db.session.commit()
            print("User 'Daniel' created successfully.")

if __name__ == '__main__':
    add_daniel()
