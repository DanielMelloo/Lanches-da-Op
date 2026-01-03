import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from database import db
from models import Subsite, Store, Item, Sector, Status

app = create_app()

def seed():
    with app.app_context():
        # Subsites
        g1 = Subsite.query.filter_by(name='G1').first()
        if not g1:
            g1 = Subsite(name='G1', active=True)
            db.session.add(g1)
            db.session.commit()
            print("Created Subsite G1")
        
        # Sectors
        if not Sector.query.filter_by(name='Recepção', subsite_id=g1.id).first():
            db.session.add(Sector(name='Recepção', subsite_id=g1.id))
            db.session.add(Sector(name='Ala A', subsite_id=g1.id))
            db.session.commit()
            print("Created Sectors for G1")

        # Stores
        store1 = Store.query.filter_by(name='Lanchonete Central', subsite_id=g1.id).first()
        if not store1:
            store1 = Store(name='Lanchonete Central', subsite_id=g1.id, active=True)
            db.session.add(store1)
            db.session.commit()
            print("Created Store Lanchonete Central")

        # Items
        if not Item.query.filter_by(name='X-Salada', subsite_id=g1.id).first():
            item1 = Item(
                name='X-Salada',
                description='Pão, carne, queijo, alface, tomate e maionese.',
                price=15.00,
                available=True,
                store_id=store1.id,
                subsite_id=g1.id,
                subitems_template={'Opcionais': ['Bacon (+2.00)', 'Ovo (+1.00)'], 'Molhos': ['Barbecue', 'Maionese Verde']}
            )
            item2 = Item(
                name='Coca-Cola Lata',
                description='350ml Gelada',
                price=5.00,
                available=True,
                store_id=store1.id,
                subsite_id=g1.id
            )
            db.session.add_all([item1, item2])
            db.session.commit()
            print("Created Items X-Salada and Coca-Cola")

        # Statuses
        if not Status.query.filter_by(name='Pendente').first():
            db.session.add(Status(name='Pendente', type='pendente', sort_order=1))
            db.session.add(Status(name='Enviado', type='enviado', sort_order=2))
            db.session.add(Status(name='Cancelado', type='finalizado', sort_order=3))
            db.session.commit()
            print("Created Statuses")

if __name__ == '__main__':
    seed()
