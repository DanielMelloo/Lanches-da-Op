from app import create_app
from models import Store, User, Subsite

app = create_app()
with app.app_context():
    print("-" * 50)
    print("STORES:")
    stores = Store.query.all()
    for s in stores:
        print(f"STORE | ID: {s.id} | Name: {s.name} | SubsiteID: {s.subsite_id} | Active: {s.active}")
    
    print("-" * 50)
    print("USERS:")
    users = User.query.all()
    for u in users:
        email = getattr(u, 'email', 'NoEmail')
        role = getattr(u, 'role', 'NoRole')
        print(f"USER  | ID: {u.id} | Email: {email} | SubsiteID: {u.subsite_id} | Role: {role}")
    
    print("-" * 50)
    print("SUBSITES:")
    subsites = Subsite.query.all()
    for s in subsites:
        print(f"SUBSITE | ID: {s.id} | Name: {s.name}")
