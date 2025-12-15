from app import create_app
from models import db, Subsite, Store, Item, User, Sector, Status
from werkzeug.security import generate_password_hash

app = create_app()

with app.app_context():
    # Create test subsite
    g2 = Subsite(name="Lanche G2", active=True, require_payment=False)
    db.session.add(g2)
    db.session.commit()
    
    # Create test store
    lanche_store = Store(name="Lanches", active=True, subsite_id=g2.id)
    db.session.add(lanche_store)
    db.session.commit()
    
    # Create test items with images
    items_data = [
        {"name": "X-Burger", "price": 12.50, "image_url": "https://images.unsplash.com/photo-1568901346375-23c9450c58cd?w=400"},
        {"name": "X-Bacon", "price": 15.00, "image_url": "https://images.unsplash.com/photo-1550547660-d9450f859349?w=400"},
        {"name": "X-Salada", "price": 10.00, "image_url": "https://images.unsplash.com/photo-1586190848861-99aa4a171e90?w=400"},
    ]
    
    for item_data in items_data:
        item = Item(
            name=item_data["name"],
            price=item_data["price"],
            image_url=item_data["image_url"],
            active=True,
            store_id=lanche_store.id
        )
        db.session.add(item)
    
    # Create test user
    test_user = User(
        name="Teste User",
        phone="11999999999",
        petro_key="TEST",
        role="user",
        subsite_id=g2.id
    )
    db.session.add(test_user)
    
    # Create test admin
    admin_user = User(
        name="Admin G2",
        phone="11988888888",
        petro_key="ADM2",
        role="admin",
        subsite_id=g2.id,
        password_hash=generate_password_hash("admin123")
    )
    db.session.add(admin_user)
    
    # Create sectors
    sectors = [
        Sector(name="Escritório", subsite_id=g2.id),
        Sector(name="Oficina", subsite_id=g2.id),
        Sector(name="Recepção", subsite_id=g2.id),
    ]
    for sector in sectors:
        db.session.add(sector)
    
    db.session.commit()
    
    print("[OK] Test data created successfully!")
    print(f"- Subsite: {g2.name} (ID: {g2.id})")
    print(f"- Store: {lanche_store.name}")
    print(f"- Items: {len(items_data)}")
    print(f"- Users: TEST (user), ADM2/admin123 (admin)")
    print(f"- Sectors: {len(sectors)}")
