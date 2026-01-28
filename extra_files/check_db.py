from app import create_app
from models import Store, User, Subsite

app = create_app()
with app.app_context():
    print("-" * 50)
    print("STORES:")
    stores = Store.query.all()
    for s in stores:
        print(f"ID: {s.id} | Name: {s.name} | Subsite ID: {s.subsite_id} | Active: {s.active}")
    
    print("-" * 50)
    print("USERS:")
    users = User.query.all()
    for u in users:
        print(f"Email: {u.email} | Role: {u.role} | Subsite ID: {u.subsite_id}")
    
    print("-" * 50)
    print("SUBSITES:")
    subsites = Subsite.query.all()
    for s in subsites:
        print(f"ID: {s.id} | Name: {s.name}")
