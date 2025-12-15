from app import create_app, db
from models import User

def restore_users():
    app = create_app()
    with app.app_context():
        users_to_add = [
            {"name": "Ailton", "petro_key": "RW98"},
            {"name": "Braga", "petro_key": "FVZN"},
            {"name": "Djenal", "petro_key": "KB3B"},
            {"name": "Fábio", "petro_key": "RW5Z"},
            {"name": "Kiyoshi", "petro_key": "R1LM"},
            {"name": "Lu", "petro_key": "RADK"},
            {"name": "Otavio", "petro_key": "R10F"},
            {"name": "Renato", "petro_key": "RW4N"},
            {"name": "WELDER", "petro_key": "AI4E"},
            {"name": "Yumi", "petro_key": "RAB9"}
        ]
        
        print(f"Checking {len(users_to_add)} users...")
        
        for u_data in users_to_add:
            existing = User.query.filter_by(petro_key=u_data['petro_key']).first()
            if not existing:
                new_user = User(
                    name=u_data['name'],
                    petro_key=u_data['petro_key'],
                    password_hash='pbkdf2:sha256:600000$Mz6...', # Placeholder or empty if auth isn't pwd based
                    role='user',
                    active=True
                )
                db.session.add(new_user)
                print(f"Preparing to add: {u_data['name']}")
            else:
                print(f"Skipping {u_data['name']} (Key {u_data['petro_key']} exists)")
        
        db.session.commit()
        print("Done!")

if __name__ == "__main__":
    restore_users()
