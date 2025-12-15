from app import create_app
from database import db
from models import User, Subsite
from werkzeug.security import generate_password_hash

app = create_app()

def create_admin():
    with app.app_context():
        g1 = Subsite.query.filter_by(name='G1').first()
        if not g1:
            print("G1 subsite not found. Run seed_data.py first.")
            return

        # Create Admin
        existing = User.query.filter_by(petro_key='ADM1').first()
        if not existing:
            admin = User(
                name='Admin G1',
                petro_key='ADM1',
                role='admin',
                subsite_id=g1.id,
                phone='99999999',
                password_hash=generate_password_hash('123456')
            )
            db.session.add(admin)
            db.session.commit()
            print("Created Admin 'ADM1' linked to G1. Password: '123456'")
        else:
            print("Admin ADM1 already exists.")

if __name__ == '__main__':
    create_admin()
