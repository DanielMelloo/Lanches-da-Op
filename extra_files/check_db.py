import json
from app import create_app
from models import Store, User, Subsite

app = create_app()
with app.app_context():
    data = {"stores": [], "users": [], "subsites": []}
    
    for s in Store.query.all():
        data["stores"].append({
            "id": s.id,
            "name": s.name,
            "subsite_id": s.subsite_id,
            "active": s.active
        })
        
    for u in User.query.all():
        data["users"].append({
            "id": u.id,
            "email": getattr(u, 'email', 'NoEmail'),
            "role": getattr(u, 'role', 'NoRole'),
            "subsite_id": u.subsite_id
        })
        
    for s in Subsite.query.all():
        data["subsites"].append({
            "id": s.id,
            "name": s.name
        })
        
    print(json.dumps(data))
