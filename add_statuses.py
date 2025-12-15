import os
# Override DB config to point to SSH Tunnel
os.environ['DB_HOST'] = '127.0.0.1:3307'
os.environ['DB_USER'] = 'root'
os.environ['DB_PASSWORD'] = 'CodeEz4ever'
os.environ['DB_NAME'] = 'lanches_da_op'
os.environ['SKIP_SCHEDULER'] = 'true'

from app import create_app
from models import db, Status

app = create_app()

with app.app_context():
    # Check if statuses already exist
    existing = Status.query.first()
    if existing:
        print("[INFO] Statuses already exist.")
    else:
        # Create default statuses
        statuses = [
            Status(name='Pendente'),
            Status(name='Confirmado'),
            Status(name='Enviado'),
            Status(name='Entregue'),
            Status(name='Cancelado'),
        ]
        
        for status in statuses:
            db.session.add(status)
        
        db.session.commit()
        print(f"[OK] {len(statuses)} status criados com sucesso!")
        for s in statuses:
            print(f"  - {s.name}")
